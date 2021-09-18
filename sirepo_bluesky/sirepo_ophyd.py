import copy

import inflection
from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus

RESERVED_OPHYD_TO_SIREPO_ATTRS = {"position": "element_position"}  # ophyd <-> sirepo
RESERVED_SIREPO_TO_OPHYD_ATTRS = {
    v: k for k, v in RESERVED_OPHYD_TO_SIREPO_ATTRS.items()
}


class SirepoSignal(Signal):
    def __init__(self, sirepo_dict, sirepo_param, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sirepo_dict = sirepo_dict
        self._sirepo_param = sirepo_param
        if sirepo_param in RESERVED_SIREPO_TO_OPHYD_ATTRS:
            self._sirepo_param = RESERVED_SIREPO_TO_OPHYD_ATTRS[sirepo_param]

    def set(self, value, *, timeout=None, settle_time=None):
        print(f"Setting value for {self.name} to {value}")
        self._sirepo_dict[self._sirepo_param] = value
        self._readback = value
        return NullStatus()

    def put(self, *args, **kwargs):
        self.set(*args, **kwargs).wait()


def create_classes(sirepo_data):
    classes = {}
    objects = {}
    data = copy.deepcopy(sirepo_data)
    for i, el in enumerate(data["models"]["beamline"]):
        for ophyd_key, sirepo_key in RESERVED_OPHYD_TO_SIREPO_ATTRS.items():
            # We have to rename the reserved attribute names. Example error
            # from ophyd:
            #
            #   TypeError: The attribute name(s) {'position'} are part of the
            #   bluesky interface and cannot be used as component names. Choose
            #   a different name.
            el[sirepo_key] = el[ophyd_key]
            el.pop(ophyd_key)

        class_name = inflection.camelize(el["title"].replace(" ", "_"))
        object_name = inflection.underscore(class_name)

        cls = type(
            class_name,
            (Device,),
            {
                k: Cpt(
                    SirepoSignal,
                    value=v,
                    sirepo_dict=sirepo_data["models"]["beamline"][i],
                    sirepo_param=k,
                )
                for k, v in el.items()
            },
        )
        classes[object_name] = cls
        objects[object_name] = cls(name=object_name)

    return classes, objects
