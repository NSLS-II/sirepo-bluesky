import copy
import hashlib
import json
import logging
from collections import deque, namedtuple

import inflection
from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus

from sirepo_bluesky.srw.srw_ophyd import (
    PropagationConfig,
    SimplePropagationConfig,
    SingleElectronSpectrumReport,
    SirepoSignalCRL,
    SirepoSignalCrystal,
    SirepoSignalGrazingAngle,
    SirepoWatchpointSRW,
)

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


class ExternalFileReference(Signal):
    """
    A pure software Signal that describe()s an image in an external file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def describe(self):
        resource_document_data = super().describe()
        resource_document_data[self.name].update(
            dict(
                external="FILESTORE:",
                dtype="array",
            )
        )
        return resource_document_data


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


class BlueskyFlyer:
    def __init__(self):
        self.name = "bluesky_flyer"
        self._asset_docs_cache = deque()
        self._resource_uids = []
        self._datum_counter = None
        self._datum_ids = []

    def kickoff(self):
        return NullStatus()

    def complete(self):
        return NullStatus()

    def collect(self):
        ...

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item


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
                base_classes = (SirepoWatchpointSRW, Device)
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
