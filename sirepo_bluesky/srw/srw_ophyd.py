import datetime
import itertools
import os
import time
from collections import OrderedDict, deque, namedtuple
from pathlib import Path

import h5py
import numpy as np
from event_model import compose_resource
from ophyd import Component as Cpt
from ophyd import Signal
from ophyd.sim import NullStatus, new_uid
from skimage.transform import resize

from sirepo_bluesky.common import DeviceWithJSONData, ExternalFileReference, SirepoSignal, create_classes, logger
from sirepo_bluesky.common.sirepo_client import SirepoClient
from sirepo_bluesky.shadow.shadow_handler import read_shadow_file
from sirepo_bluesky.srw.srw_handler import read_srw_file


class SirepoWatchpointSRW(DeviceWithJSONData):
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
        image_shape=(1024, 1024),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._root_dir = root_dir
        self._assets_dir = assets_dir
        self._result_file = result_file
        self._image_shape = image_shape

        self._asset_docs_cache = deque()
        self._resource_document = None
        self._datum_factory = None

        self._sim_type = self.connection.data["simulationType"]
        allowed_sim_types = ("srw", "shadow", "madx")
        if self._sim_type not in allowed_sim_types:
            raise RuntimeError(
                f"Unknown simulation type: {self._sim_type}\nAllowed simulation types: {allowed_sim_types}"
            )

    def stage(self):
        super().stage()
        date = datetime.datetime.now()
        self._assets_dir = date.strftime("%Y/%m/%d")
        data_file = f"{new_uid()}.h5"

        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec=f'{self.connection.data["simulationType"]}_hdf5'.upper(),
            root=self._root_dir,
            resource_path=str(Path(self._assets_dir) / Path(data_file)),
            resource_kwargs={},
        )

        self._data_file = str(
            Path(self._resource_document["root"]) / Path(self._resource_document["resource_path"])
        )

        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        self._h5file_desc = h5py.File(self._data_file, "x")
        group = self._h5file_desc.create_group("/entry")
        self._dataset = group.create_dataset(
            "image",
            data=np.full(fill_value=np.nan, shape=(1, *self._image_shape)),
            maxshape=(None, *self._image_shape),
            chunks=(1, *self._image_shape),
            dtype="float64",
            compression="lzf",
        )
        self._counter = itertools.count()

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")
        current_frame = next(self._counter)
        # TODO: revisit this for shadow
        sim_result_file = f"{os.path.splitext(self._data_file)[0]}_{self._sim_type}_{current_frame:04d}.dat"

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
            # TODO: rename _image_shape to _target_image_shape?
            data = resize(ret["data"], self._image_shape)
            self._dataset.resize((current_frame + 1, *self._image_shape))

            logger.debug(f"{self._dataset = }\n{self._dataset.shape = }")

            self._dataset[current_frame, :, :] = data

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

        datum_document = self._datum_factory(datum_kwargs={"frame": current_frame})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        logger.debug(f"\nReport for {self.name}: {self.connection.data['report']}\n")

        # We call the trigger on super at the end to update the sirepo_data_json
        # and the corresponding hash after the simulation is run.
        super().trigger(*args, **kwargs)
        return NullStatus()

    def describe(self):
        res = super().describe()

        sim_type = self.connection.data["simulationType"]

        res[self.image.name].update(dict(external="FILESTORE"))

        for key in [self.shape.name]:
            res[key].update(dict(dtype_str="<i8"))

        for key in [self.vertical_extent.name, self.horizontal_extent.name]:
            res[key].update(dict(dtype_str="<f8"))

        if sim_type == "shadow":
            # TODO: dynamic watchpointReport number
            ny = nx = self.connection.data["models"]["watchpointReport12"]["histogramBins"]
            res[self.image.name].update(dict(shape=(ny, nx)))

        if sim_type == "srw":
            # TODO: more fixes depending on report
            if (
                self.connection.data["report"].startswith("watchpointReport")
                or self.connection.data["report"] == "initialIntensityReport"
            ):
                res[self.image.name].update(dict(shape=self._image_shape))
            elif self.connection.data["report"] == "intensityReport":
                num_points = self.connection.data["models"]["intensityReport"]["photonEnergyPointCount"]
                res[self.image.name].update(dict(shape=(num_points,)))
            else:
                raise ValueError(f"Unknown report type: {self.connection.data['report']}")

        return res

    def unstage(self):
        super().unstage()
        self._resource_document = None
        self._datum_factory = None
        del self._dataset
        self._h5file_desc.close()

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


# This is for backwards compatibility
SirepoWatchpoint = SirepoWatchpointSRW


class SingleElectronSpectrumReport(SirepoWatchpointSRW):
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

    emptysim = SirepoClient("http://localhost:8000")
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
