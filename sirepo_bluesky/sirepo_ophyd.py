import copy
import datetime
import json
from collections import deque
from pathlib import Path

import inflection
from event_model import compose_resource
from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus, new_uid

from . import ExternalFileReference
from .srw_handler import read_srw_file

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


class SirepoWatchpoint(Device):

    image = Cpt(ExternalFileReference, kind="normal")
    shape = Cpt(Signal)
    mean = Cpt(Signal, kind="hinted")
    photon_energy = Cpt(Signal, kind="normal")
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)
    sirepo_json = Cpt(Signal, kind="normal", value="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._asset_docs_cache = deque()
        self._resource_document = None
        self._datum_factory = None

        self._ndim = 2

        self._root_dir = "/tmp/srw_det_data"
        self.sirepo_server = "http://localhost:8000"
        # self.data may not be needed as it's handled by self.connection now.
        # self.data = None

    def trigger(self, *args, **kwargs):
        super().trigger(*args, **kwargs)
        print(f"Custom trigger for {self.name}")

        date = datetime.datetime.now()
        file_name = new_uid()
        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec="srw",
            root=self._root_dir,
            resource_path=str(
                Path(date.strftime("%Y/%m/%d")) / Path(f"{file_name}.dat")
            ),
            resource_kwargs={},
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        sim_result_file = str(
            Path(self._resource_document["root"])
            / Path(self._resource_document["resource_path"])
        )

        self.connection.data["report"] = f"watchpointReport{self.id._sirepo_dict['id']}"
        self.connection.run_simulation()

        datafile = self.connection.get_datafile()

        with open(sim_result_file, "wb") as f:
            f.write(datafile)

        self._resource_document["resource_kwargs"]["ndim"] = self._ndim

        def update_components(_data):
            self.shape.put(_data["shape"])
            self.mean.put(_data["mean"])
            self.photon_energy.put(_data["photon_energy"])
            self.horizontal_extent.put(_data["horizontal_extent"])
            self.vertical_extent.put(_data["vertical_extent"])

        ret = read_srw_file(sim_result_file, ndim=self._ndim)
        update_components(ret)

        datum_document = self._datum_factory(datum_kwargs={})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        self.sirepo_json.put(json.dumps(self.connection.data))

        self._resource_document = None
        self._datum_factory = None

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


def create_classes(sirepo_data, connection, create_objects=True):
    classes = {}
    objects = {}
    data = copy.deepcopy(sirepo_data)
    for i, el in enumerate(data["models"]["beamline"]):
        print(f"Processing {el}...")
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

        base_classes = (Device,)
        extra_kwargs = {}
        if el["type"] == "watch":
            base_classes = (SirepoWatchpoint, Device)
            extra_kwargs = {"connection": connection}

        components = {}
        for k, v in el.items():
            components[k] = Cpt(
                SirepoSignal,
                value=v,
                sirepo_dict=sirepo_data["models"]["beamline"][i],
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

    return classes, objects
