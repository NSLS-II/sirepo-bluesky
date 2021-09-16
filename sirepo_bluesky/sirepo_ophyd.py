import copy

from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus


class SirepoSignal(Signal):
    def __init__(self, sirepo_dict, sirepo_param, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sirepo_dict = sirepo_dict
        self._sirepo_param = sirepo_param.replace("element_position", "position")

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
    keys_to_remove = {"position"}
    data = copy.deepcopy(sirepo_data)
    for i, el in enumerate(data["models"]["beamline"]):
        for key in keys_to_remove:
            el[f"element_{key}"] = el[key]
            el.pop(key)
        el["title"] = el["title"].replace(" ", "")
        title = el["title"]
        cls = type(
            title,
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
        classes[title] = cls
        objects[title] = cls(name=title)

    return classes, objects
