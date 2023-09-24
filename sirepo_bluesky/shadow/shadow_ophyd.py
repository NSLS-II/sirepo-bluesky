import datetime
import json
import time as ttime
from pathlib import Path

from event_model import compose_resource
from ophyd import Component as Cpt
from ophyd import Signal
from ophyd.sim import NullStatus, new_uid

from sirepo_bluesky.common import logger
from sirepo_bluesky.common.base_classes import DeviceWithJSONData, SirepoWatchpointBase
from sirepo_bluesky.shadow.shadow_handler import read_shadow_file


class SirepoWatchpointShadow(SirepoWatchpointBase):
    def __init__(
        self,
        *args,
        root_dir="/tmp/sirepo-bluesky-data",
        assets_dir=None,
        result_file=None,
        **kwargs,
    ):
        self._allowed_sim_types = ("shadow",)
        super().__init__(*args, root_dir=root_dir, assets_dir=assets_dir, result_file=result_file, **kwargs)

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        self.connection.data["report"] = self._report

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

        _, duration = self.connection.run_simulation()
        self.duration.put(duration)

        datafile = self.connection.get_datafile(file_index=-1)

        with open(sim_result_file, "wb") as f:
            f.write(datafile)

        conn_data = self.connection.data
        nbins = conn_data["models"][self._report]["histogramBins"]
        ret = read_shadow_file(sim_result_file, histogram_bins=nbins)
        self._resource_document["resource_kwargs"]["histogram_bins"] = nbins

        def update_components(_data):
            # self.shape.put(_data["shape"])
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
        ny = nx = self.connection.data["models"][self._report]["histogramBins"]
        res[self.image.name].update(dict(external="FILESTORE", shape=(ny, nx)))
        return res


# This is for backwards compatibility
SirepoWatchpoint = SirepoWatchpointShadow


class BeamStatisticsReport(DeviceWithJSONData):
    # NOTE: TES aperture changes don't seem to change the beam statistics
    # report graph on the website?

    report = Cpt(Signal, value="", kind="normal")  # values are always strings, not dictionaries

    def __init__(self, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = connection
        self._report = "beamStatisticsReport"

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        self.connection.data["report"] = self._report

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
