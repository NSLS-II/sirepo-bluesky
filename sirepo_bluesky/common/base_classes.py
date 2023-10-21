import hashlib
import json
from collections import deque

from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus

from sirepo_bluesky.common import ExternalFileReference


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


class SirepoWatchpointBase(DeviceWithJSONData):
    image = Cpt(ExternalFileReference, kind="normal")
    flux = Cpt(Signal, kind="hinted")
    mean = Cpt(Signal, kind="normal")
    x = Cpt(Signal, kind="normal")
    y = Cpt(Signal, kind="normal")
    fwhm_x = Cpt(Signal, kind="normal")
    fwhm_y = Cpt(Signal, kind="normal")
    photon_energy = Cpt(Signal, kind="normal")
    horizontal_extent_start = Cpt(Signal)
    horizontal_extent_end = Cpt(Signal)
    vertical_extent_start = Cpt(Signal)
    vertical_extent_end = Cpt(Signal)

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

        self._sim_type = self.connection.data["simulationType"]
        if self._sim_type not in self._allowed_sim_types:
            raise RuntimeError(
                f"Unknown simulation type: {self._sim_type}\nAllowed simulation types: {self._allowed_sim_types}"
            )

        self._report = None
        if hasattr(self, "id"):
            self._report = f"watchpointReport{self.id._sirepo_dict['id']}"

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item
