import copy
import datetime
import hashlib
import json
import logging
import time
from collections import OrderedDict, deque, namedtuple
from pathlib import Path

import inflection
from event_model import compose_resource
from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus, new_uid

from sirepo_bluesky.sirepo_bluesky import SirepoBluesky

from . import ExternalFileReference
from .shadow_handler import read_shadow_file
from .srw_handler import read_srw_file

logger = logging.getLogger("sirepo-bluesky")
# Note: the following handler could be created/added to the logger on the client side:
# import sys
# stream_handler = logging.StreamHandler(sys.stdout)
# logger.addHandler(stream_handler)

RESERVED_OPHYD_TO_SIREPO_ATTRS = {  # ophyd <-> sirepo
    "position": "element_position",
    "name": "element_name",
    "class": "command_class",
}
RESERVED_SIREPO_TO_OPHYD_ATTRS = {v: k for k, v in RESERVED_OPHYD_TO_SIREPO_ATTRS.items()}


class SirepoSignal(Signal):
    def __init__(self, sirepo_dict, sirepo_param, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sirepo_dict = sirepo_dict
        self._sirepo_param = sirepo_param
        if sirepo_param in RESERVED_SIREPO_TO_OPHYD_ATTRS:
            self._sirepo_param = RESERVED_SIREPO_TO_OPHYD_ATTRS[sirepo_param]

    def set(self, value, *, timeout=None, settle_time=None):
        logger.debug(f"Setting value for {self.name} to {value}")
        self._sirepo_dict[self._sirepo_param] = value
        self._readback = value
        return NullStatus()

    def put(self, *args, **kwargs):
        self.set(*args, **kwargs).wait()


class ReadOnlyException(Exception):
    ...


class SirepoSignalRO(SirepoSignal):
    def set(self, *args, **kwargs):
        raise ReadOnlyException("Cannot set/put the read-only signal.")


class DeviceWithJSONData(Device):
    sirepo_data_json = Cpt(Signal, kind="normal", value="")
    sirepo_data_hash = Cpt(Signal, kind="normal", value="")
    duration = Cpt(Signal, kind="normal", value=-1.0)

    def trigger(self, *args, **kwargs):
        super().trigger(*args, **kwargs)

        json_str = json.dumps(self.connection.data)
        json_hash = hashlib.sha256(json_str.encode()).hexdigest()
        self.sirepo_data_json.put(json_str)
        self.sirepo_data_hash.put(json_hash)

        return NullStatus()


class SirepoWatchpoint(DeviceWithJSONData):
    image = Cpt(ExternalFileReference, kind="normal")
    shape = Cpt(Signal)
    flux = Cpt(Signal, kind="hinted")
    mean = Cpt(Signal, kind="normal")
    x = Cpt(Signal, kind="normal")
    y = Cpt(Signal, kind="normal")
    fwhm_x = Cpt(Signal, kind="normal")
    fwhm_y = Cpt(Signal, kind="normal")
    photon_energy = Cpt(Signal, kind="normal")
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)

    def __init__(
        self,
        *args,
        root_dir="/tmp/sirepo-bluesky-data",
        assets_dir=None,
        result_file=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._root_dir = root_dir
        self._assets_dir = assets_dir
        self._result_file = result_file

        self._asset_docs_cache = deque()
        self._resource_document = None
        self._datum_factory = None

        sim_type = self.connection.data["simulationType"]
        allowed_sim_types = ("srw", "shadow", "madx")
        if sim_type not in allowed_sim_types:
            raise RuntimeError(
                f"Unknown simulation type: {sim_type}\nAllowed simulation types: {allowed_sim_types}"
            )

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        date = datetime.datetime.now()
        self._assets_dir = date.strftime("%Y/%m/%d")
        self._result_file = f"{new_uid()}.dat"

        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec=self.connection.data["simulationType"],
            root=self._root_dir,
            resource_path=str(Path(self._assets_dir) / Path(self._result_file)),
            resource_kwargs={},
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        sim_result_file = str(
            Path(self._resource_document["root"]) / Path(self._resource_document["resource_path"])
        )

        self.connection.data["report"] = f"watchpointReport{self.id._sirepo_dict['id']}"

        _, duration = self.connection.run_simulation()
        self.duration.put(duration)

        datafile = self.connection.get_datafile(file_index=-1)

        with open(sim_result_file, "wb") as f:
            f.write(datafile)

        conn_data = self.connection.data
        sim_type = conn_data["simulationType"]
        if sim_type == "srw":
            ndim = 2  # this will always be a report with 2D data.
            ret = read_srw_file(sim_result_file, ndim=ndim)
            self._resource_document["resource_kwargs"]["ndim"] = ndim
        elif sim_type == "shadow":
            nbins = conn_data["models"][conn_data["report"]]["histogramBins"]
            ret = read_shadow_file(sim_result_file, histogram_bins=nbins)
            self._resource_document["resource_kwargs"]["histogram_bins"] = nbins

        def update_components(_data):
            self.shape.put(_data["shape"])
            self.flux.put(_data["flux"])
            self.mean.put(_data["mean"])
            self.x.put(_data["x"])
            self.y.put(_data["y"])
            self.fwhm_x.put(_data["fwhm_x"])
            self.fwhm_y.put(_data["fwhm_y"])
            self.photon_energy.put(_data["photon_energy"])
            self.horizontal_extent.put(_data["horizontal_extent"])
            self.vertical_extent.put(_data["vertical_extent"])

        update_components(ret)

        datum_document = self._datum_factory(datum_kwargs={})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        self._resource_document = None
        self._datum_factory = None

        logger.debug(f"\nReport for {self.name}: {self.connection.data['report']}\n")

        # We call the trigger on super at the end to update the sirepo_data_json
        # and the corresponding hash after the simulation is run.
        super().trigger(*args, **kwargs)
        return NullStatus()

    def describe(self):
        res = super().describe()
        res[self.image.name].update(dict(external="FILESTORE"))
        return res

    def unstage(self):
        super().unstage()
        self._resource_document = None

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


class SingleElectronSpectrumReport(SirepoWatchpoint):
    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        date = datetime.datetime.now()
        self._assets_dir = date.strftime("%Y/%m/%d")
        self._result_file = f"{new_uid()}.dat"

        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec=self.connection.data["simulationType"],
            root=self._root_dir,
            resource_path=str(Path(self._assets_dir) / Path(self._result_file)),
            resource_kwargs={},
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        sim_result_file = str(
            Path(self._resource_document["root"]) / Path(self._resource_document["resource_path"])
        )

        self.connection.data["report"] = "intensityReport"

        start_time = time.monotonic()
        self.connection.run_simulation()
        self.duration.put(time.monotonic() - start_time)

        datafile = self.connection.get_datafile()

        with open(sim_result_file, "wb") as f:
            f.write(datafile)

        conn_data = self.connection.data
        sim_type = conn_data["simulationType"]
        if sim_type == "srw":
            ndim = 1
            ret = read_srw_file(sim_result_file, ndim=ndim)
            self._resource_document["resource_kwargs"]["ndim"] = ndim

        def update_components(_data):
            self.shape.put(_data["shape"])
            self.flux.put(_data["flux"])
            self.mean.put(_data["mean"])
            self.x.put(_data["x"])
            self.y.put(_data["y"])
            self.fwhm_x.put(_data["fwhm_x"])
            self.fwhm_y.put(_data["fwhm_y"])
            self.photon_energy.put(_data["photon_energy"])
            self.horizontal_extent.put(_data["horizontal_extent"])
            self.vertical_extent.put(_data["vertical_extent"])

        update_components(ret)

        datum_document = self._datum_factory(datum_kwargs={})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        self._resource_document = None
        self._datum_factory = None

        logger.debug(f"\nReport for {self.name}: {self.connection.data['report']}\n")

        return NullStatus()


class BeamStatisticsReport(DeviceWithJSONData):
    # NOTE: TES aperture changes don't seem to change the beam statistics
    # report graph on the website?

    report = Cpt(Signal, value="", kind="normal")  # values are always strings, not dictionaries

    def __init__(self, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        self.connection.data["report"] = "beamStatisticsReport"

        start_time = time.monotonic()
        self.connection.run_simulation()
        self.duration.put(time.monotonic() - start_time)

        datafile = self.connection.get_datafile(file_index=-1)
        self.report.put(json.dumps(json.loads(datafile.decode())))

        logger.debug(f"\nReport for {self.name}: {self.connection.data['report']}\n")

        # We call the trigger on super at the end to update the sirepo_data_json
        # and the corresponding hash after the simulation is run.
        super().trigger(*args, **kwargs)
        return NullStatus()

    def stage(self):
        super().stage()
        self.report.put("")

    def unstage(self):
        super().unstage()
        self.report.put("")


class SirepoSignalGrazingAngle(SirepoSignal):
    def set(self, value):
        super().set(value)
        ret = self.parent.connection.compute_grazing_orientation(self._sirepo_dict)
        # State is added to the ret dict from compute_grazing_orientation and we
        # want to make sure the vectors are updated properly every time the
        # grazing angle is updated.
        ret.pop("state")
        # Update vector components
        for cpt in [
            "normalVectorX",
            "normalVectorY",
            "normalVectorZ",
            "tangentialVectorX",
            "tangentialVectorY",
        ]:
            getattr(self.parent, cpt).put(ret[cpt])
        return NullStatus()


class SirepoSignalCRL(SirepoSignal):
    def set(self, value):
        super().set(value)
        ret = self.parent.connection.compute_crl_characteristics(self._sirepo_dict)
        # State is added to the ret dict from compute_crl_characteristics and we
        # want to make sure the crl element is updated properly when parameters are changed.
        ret.pop("state")
        # Update crl element
        for cpt in ["absoluteFocusPosition", "focalDistance"]:
            getattr(self.parent, cpt).put(ret[cpt])
        return NullStatus()


class SirepoSignalCrystal(SirepoSignal):
    def set(self, value):
        super().set(value)
        ret = self.parent.connection.compute_crystal_orientation(self._sirepo_dict)
        # State is added to the ret dict from compute_crystal_orientation and we
        # want to make sure the crystal element is updated properly when parameters are changed.
        ret.pop("state")
        # Update crystal element
        for cpt in [
            "dSpacing",
            "grazingAngle",
            "nvx",
            "nvy",
            "nvz",
            "outframevx",
            "outframevy",
            "outoptvx",
            "outoptvy",
            "outoptvz",
            "psi0i",
            "psi0r",
            "psiHBi",
            "psiHBr",
            "psiHi",
            "psiHr",
            "tvx",
            "tvy",
        ]:
            getattr(self.parent, cpt).put(ret[cpt])
        return NullStatus()


SimplePropagationConfig = namedtuple(
    "PropagationConfig",
    "resize_before resize_after precision propagator_type "
    + "fourier_resize hrange_mod hres_mod vrange_mod vres_mod",
)


class PropagationConfig(SimplePropagationConfig):
    read_attrs = list(SimplePropagationConfig._fields)
    component_names = SimplePropagationConfig._fields

    def read(self):
        read_attrs = self.read_attrs
        propagation_read = OrderedDict()
        for field in read_attrs:
            propagation_read[field] = getattr(self, field).read()
        return propagation_read


def create_classes(connection, create_objects=True, extra_model_fields=[]):
    classes = {}
    objects = {}
    data = copy.deepcopy(connection.data)

    sim_type = connection.sim_type

    SimTypeConfig = namedtuple("SimTypeConfig", "element_location class_name_field")

    srw_config = SimTypeConfig("beamline", "title")
    shadow_config = SimTypeConfig("beamline", "title")
    madx_config = SimTypeConfig("elements", "element_name")

    config_dict = {
        "srw": srw_config,
        "shadow": shadow_config,
        "madx": madx_config,
    }

    model_fields = [config_dict[sim_type].element_location] + extra_model_fields

    data_models = {}
    for model_field in model_fields:
        if sim_type == "srw" and model_field in ["undulator", "intensityReport"]:
            if model_field == "intensityReport":
                title = "SingleElectronSpectrum"
            else:
                title = model_field
            data["models"][model_field].update({"title": title, "type": model_field})
            data_models[model_field] = [data["models"][model_field]]
        else:
            data_models[model_field] = data["models"][model_field]

    for model_field, data_model in data_models.items():
        for i, el in enumerate(data_model):  # 'el' is a dict, 'data_model' is a list of dicts
            logger.debug(f"Processing {el}...")

            for ophyd_key, sirepo_key in RESERVED_OPHYD_TO_SIREPO_ATTRS.items():
                # We have to rename the reserved attribute names. Example error
                # from ophyd:
                #
                #   TypeError: The attribute name(s) {'position'} are part of the
                #   bluesky interface and cannot be used as component names. Choose
                #   a different name.
                if ophyd_key in el:
                    el[sirepo_key] = el[ophyd_key]
                    el.pop(ophyd_key)
                else:
                    pass

            class_name = el[config_dict[sim_type].class_name_field]
            if model_field == "commands":
                # Use command type and index in the model as class name to
                # prevent overwriting any other elements or rpnVariables
                # Examples of class names: beam0, select1, twiss7
                class_name = inflection.camelize(f"{el['_type']}{i}")
            else:
                class_name = inflection.camelize(
                    el[config_dict[sim_type].class_name_field].replace(" ", "_").replace(".", "").replace("-", "_")
                )
            object_name = inflection.underscore(class_name)

            base_classes = (Device,)
            extra_kwargs = {"connection": connection}
            if "type" in el and el["type"] == "watch":
                base_classes = (SirepoWatchpoint, Device)
            elif "type" in el and el["type"] == "intensityReport":
                base_classes = (SingleElectronSpectrumReport, Device)

            components = {}
            for k, v in el.items():
                if (
                    "type" in el
                    and el["type"] in ["sphericalMirror", "toroidalMirror", "ellipsoidMirror"]
                    and k == "grazingAngle"
                ):
                    cpt_class = SirepoSignalGrazingAngle
                elif "type" in el and el["type"] == "crl" and k not in ["absoluteFocusPosition", "focalDistance"]:
                    cpt_class = SirepoSignalCRL
                elif (
                    "type" in el
                    and el["type"] == "crystal"
                    and k
                    not in [
                        "dSpacing",
                        "grazingAngle",
                        "nvx",
                        "nvy",
                        "nvz",
                        "outframevx",
                        "outframevy",
                        "outoptvx",
                        "outoptvy",
                        "outoptvz",
                        "psi0i",
                        "psi0r",
                        "psiHBi",
                        "psiHBr",
                        "psiHi",
                        "psiHr",
                        "tvx",
                        "tvy",
                    ]
                ):
                    cpt_class = SirepoSignalCrystal
                else:
                    # TODO: Cover the cases for mirror and crystal grazing angles
                    cpt_class = SirepoSignal

                if "type" in el and el["type"] not in ["undulator", "intensityReport"]:
                    sirepo_dict = connection.data["models"][model_field][i]
                elif sim_type == "madx" and model_field in ["rpnVariables", "commands"]:
                    sirepo_dict = connection.data["models"][model_field][i]
                else:
                    sirepo_dict = connection.data["models"][model_field]

                components[k] = Cpt(
                    cpt_class,
                    value=(float(v) if type(v) is int else v),
                    sirepo_dict=sirepo_dict,
                    sirepo_param=k,
                )
            components.update(**extra_kwargs)

            cls = type(
                class_name,
                base_classes,
                components,
            )

            classes[object_name] = cls
            if create_objects:
                objects[object_name] = cls(name=object_name)

            if sim_type == "srw" and model_field == "beamline":
                prop_params = connection.data["models"]["propagation"][str(el["id"])][0]
                sirepo_propagation = []
                object_name += "_propagation"
                for i in range(9):
                    sirepo_propagation.append(
                        SirepoSignal(
                            name=f"{object_name}_{SimplePropagationConfig._fields[i]}",
                            value=float(prop_params[i]),
                            sirepo_dict=prop_params,
                            sirepo_param=i,
                        )
                    )
                if create_objects:
                    objects[object_name] = PropagationConfig(*sirepo_propagation[:])

        if sim_type == "srw":
            post_prop_params = connection.data["models"]["postPropagation"]
            sirepo_propagation = []
            object_name = "post_propagation"
            for i in range(9):
                sirepo_propagation.append(
                    SirepoSignal(
                        name=f"{object_name}_{SimplePropagationConfig._fields[i]}",
                        value=float(post_prop_params[i]),
                        sirepo_dict=post_prop_params,
                        sirepo_param=i,
                    )
                )
            classes["propagation_parameters"] = PropagationConfig
            if create_objects:
                objects[object_name] = PropagationConfig(*sirepo_propagation[:])

    return classes, objects


def populate_beamline(sim_name, *args):
    """
    Parameters
    ----------
    *args :
        For one beamline, ``connection, indices, new_positions``.
        In general:

        .. code-block:: python

            connection1, indices1, new_positions1
            connection2, indices2, new_positions2
            ...,
            connectionN, indicesN, new_positionsN
    """
    if len(args) % 3 != 0:
        raise ValueError(
            "Incorrect signature, arguments must be of the signature: connection, indices, new_positions, ..."
        )

    connections = []
    indices_list = []
    new_positions_list = []

    for i in range(0, len(args), 3):
        connections.append(args[i])
        indices_list.append(args[i + 1])
        new_positions_list.append(args[i + 2])

    emptysim = SirepoBluesky("http://localhost:8000")
    emptysim.auth("srw", sim_id="emptysim")
    new_beam = emptysim.copy_sim(sim_name=sim_name)
    new_beamline = new_beam.data["models"]["beamline"]
    new_propagation = new_beam.data["models"]["propagation"]

    curr_id = 0
    for connection, indices, new_positions in zip(connections, indices_list, new_positions_list):
        old_beamline = connection.data["models"]["beamline"]
        old_propagation = connection.data["models"]["propagation"]
        for i, pos in zip(indices, new_positions):
            new_beamline.append(old_beamline[i].copy())
            new_beamline[curr_id]["id"] = curr_id
            new_beamline[curr_id]["position"] = pos
            new_propagation[str(curr_id)] = old_propagation[str(old_beamline[i]["id"])].copy()
            curr_id += 1

    classes, objects = create_classes(new_beam)

    return new_beam, classes, objects
