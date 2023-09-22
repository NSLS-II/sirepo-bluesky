import copy
from collections import namedtuple

import inflection
from ophyd import Component as Cpt
from ophyd import Device

from sirepo_bluesky.common import RESERVED_OPHYD_TO_SIREPO_ATTRS, SirepoSignal, logger
from sirepo_bluesky.srw.srw_ophyd import (
    PropagationConfig,
    SimplePropagationConfig,
    SingleElectronSpectrumReport,
    SirepoSignalCRL,
    SirepoSignalCrystal,
    SirepoSignalGrazingAngle,
    SirepoWatchpointSRW,
)


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
                # TODO: fix for shadow
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
