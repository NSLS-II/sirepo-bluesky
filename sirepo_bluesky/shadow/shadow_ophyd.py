import datetime
import json
import time as ttime
from collections import deque
from pathlib import Path

from event_model import compose_resource
from ophyd import Component as Cpt
from ophyd import Signal
from ophyd.sim import NullStatus, new_uid

from sirepo_bluesky.common import DeviceWithJSONData, ExternalFileReference, logger
from sirepo_bluesky.shadow.shadow_handler import read_shadow_file
from sirepo_bluesky.srw.srw_handler import read_srw_file


class SirepoWatchpointShadow(DeviceWithJSONData):
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


# This is for backwards compatibility
SirepoWatchpoint = SirepoWatchpointShadow


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

        start_time = ttime.monotonic()
        self.connection.run_simulation()
        self.duration.put(ttime.monotonic() - start_time)

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
