import datetime
import json
from collections import deque
from enum import Enum, unique
from pathlib import Path

import unyt as u
from event_model import compose_resource
from ophyd import Component as Cpt
from ophyd import Device, Signal
from ophyd.sim import NullStatus, SynAxis, new_uid

from . import ExternalFileReference
from .shadow_handler import read_shadow_file
from .sirepo_bluesky import SirepoBluesky


@unique
class ShadowSimReportTypes(Enum):
    default_report = "default_report"
    beam_stats_report = "beam_stats_report"


class SirepoShadowDetector(Device):
    """
    Use SRW code based on the value of the motor.

    Units used in plots are directly from sirepo. View the schema at:
    https://github.com/radiasoft/sirepo/blob/master/sirepo/package_data/static/json/srw-schema.json

    Parameters
    ----------
    name : str
        The name of the detector
    sim_id : str
        The simulation id corresponding to the Sirepo simulation being run on
        local server
    watch_name : str
        The name of the watchpoint viewing the simulation
    sirepo_server : str
        Address that identifies access to local Sirepo server
    source_simulation : bool
        States whether user wants to grab source page info instead of beamline

    """

    image = Cpt(ExternalFileReference, kind="normal")
    shape = Cpt(Signal)
    mean = Cpt(Signal, kind="hinted")
    duration = Cpt(Signal, kind="hinted")
    photon_energy = Cpt(Signal, kind="normal")
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)
    sirepo_json = Cpt(Signal, kind="normal", value="")
    beam_statistics_report = Cpt(Signal, kind="omitted", value="")

    def __init__(
        self,
        name="sirepo_det",
        sim_report_type=ShadowSimReportTypes.default_report.name,
        sim_id=None,
        watch_name=None,
        sirepo_server="http://10.10.10.10:8000",
        source_simulation=False,
        root_dir="/tmp/sirepo_det_data",
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)

        allowed_sim_report_types = tuple(ShadowSimReportTypes.__members__.keys())
        if sim_report_type not in allowed_sim_report_types:
            raise ValueError(
                f"sim_report_type should be one of {allowed_sim_report_types}. "
                f"Provided value: {sim_report_type}"
            )

        if sim_id is None:
            raise ValueError(f"Simulation ID must be provided. Currently it is set to {sim_id}")

        self._asset_docs_cache = deque()
        self._resource_document = None
        self._datum_factory = None

        self._root_dir = root_dir

        self.sirepo_component = None
        self.fields = {}
        self.field_units = {}
        self.parents = {}
        self._result = {}
        self._sim_type = "shadow"
        self._sim_report_type = sim_report_type
        self._sim_id = sim_id
        self.watch_name = watch_name
        self.sb = None
        self.data = None
        self._hints = None
        self.sirepo_server = sirepo_server
        self.parameters = None
        self.source_parameters = None
        self.optic_parameters = {}
        self.sirepo_components = None
        self.source_component = None
        self.active_parameters = {}
        self.autocompute_params = {}
        self.source_simulation = source_simulation
        # from srw self.one_d_reports = ['intensityReport']
        self.two_d_reports = ["watchpointReport"]

        self.connect(sim_type=self._sim_type, sim_id=self._sim_id)

    def update_value(self, value, units):
        unyt_obj = u.m
        starting_unit = value * unyt_obj
        converted_unit = starting_unit.to(units)
        return converted_unit

    """
    Get new parameter values from Sirepo server

    """

    def update_parameters(self):
        data, sirepo_schema = self.sb.auth(self._sim_type, self._sim_id)
        self.data = data
        for key, value in self.sirepo_components.items():
            optic_id = self.sb.find_optic_id_by_name(key)
            self.parameters = {f"sirepo_{k}": v for k, v in data["models"]["beamline"][optic_id].items()}
            for k, v in self.parameters.items():
                getattr(value, k).set(v)

    def trigger(self):
        super().trigger()

        date = datetime.datetime.now()
        file_name = new_uid()
        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec=self._sim_type,
            root=self._root_dir,
            resource_path=str(Path(date.strftime("%Y/%m/%d")) / Path(f"{file_name}.dat")),
            resource_kwargs={},
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        sim_result_file = str(
            Path(self._resource_document["root"]) / Path(self._resource_document["resource_path"])
        )

        if not self.source_simulation:
            if self.sirepo_component is not None:
                for component in self.data["models"]["beamline"]:
                    if "autocomputeVectors" in component.keys():
                        self.autocompute_params[component["title"]] = component["autocomputeVectors"]
                for i in range(len(self.active_parameters)):
                    real_field = self.fields["field" + str(i)].replace("sirepo_", "")
                    dict_key = self.fields["field" + str(i)].replace("sirepo", self.parents["par" + str(i)])
                    x = self.active_parameters[dict_key].read()[
                        f'{self.parents["par" + str(i)]}_{self.fields["field" + str(i)]}'
                    ]["value"]
                    element = self.sb.find_element(
                        self.data["models"]["beamline"],
                        "title",
                        self.parents["par" + str(i)],
                    )
                    element[real_field] = x
                    if self.parents[f"par{i}"] in self.autocompute_params.keys() and "grazingAngle" in dict_key:
                        grazing_vecs_dict = {}
                        autocompute_key = f'{self.parents[f"par{i}"]}_sirepo_autocomputeVectors'
                        autocompute_type = self.sirepo_components[self.parents[f"par{i}"]].read()[autocompute_key][
                            "value"
                        ]
                        grazing_vecs_dict["angle"] = x
                        grazing_vecs_dict["autocompute_type"] = autocompute_type
                        optic_id = self.sb.find_optic_id_by_name(self.parents[f"par{i}"])
                        self.sb.update_grazing_vectors(
                            self.data["models"]["beamline"][optic_id], grazing_vecs_dict
                        )

                watch = self.sb.find_element(self.data["models"]["beamline"], "title", self.watch_name)

                if self._sim_report_type == ShadowSimReportTypes.beam_stats_report.name:
                    self.data["report"] = "beamStatisticsReport"
                    self.beam_statistics_report.kind = "normal"
                elif self._sim_report_type == ShadowSimReportTypes.default_report.name:
                    self.data["report"] = "watchpointReport{}".format(watch["id"])
                    self.beam_statistics_report.kind = "normal"
                else:
                    raise ValueError(f"Unknown simulation report type: {self._sim_report_type}")

        # elif self._sim_report_type == SimReportTypes.srw_se_spectrum.name:
        #     self.data['report'] = "intensityReport"
        _, duration = self.sb.run_simulation()
        self.duration.put(duration)

        datafile = self.sb.get_datafile(file_index=-1)
        if self._sim_report_type == ShadowSimReportTypes.beam_stats_report.name:
            self.beam_statistics_report.put(json.dumps(json.loads(datafile.decode())))
        else:
            with open(sim_result_file, "wb") as f:
                f.write(datafile)

        def update_components(_data):
            self.shape.put(_data["shape"])
            self.mean.put(_data["mean"])
            self.photon_energy.put(_data["photon_energy"])
            self.horizontal_extent.put(_data["horizontal_extent"])
            self.vertical_extent.put(_data["vertical_extent"])

        if not self._sim_report_type == ShadowSimReportTypes.beam_stats_report.name:
            nbins = self.data["models"][self.data["report"]]["histogramBins"]
            ret = read_shadow_file(sim_result_file, histogram_bins=nbins)
            self._resource_document["resource_kwargs"]["histogram_bins"] = nbins
            update_components(ret)

        datum_document = self._datum_factory(datum_kwargs={})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        self.sirepo_json.put(json.dumps(self.data))

        self._resource_document = None
        self._datum_factory = None

        super().trigger()
        return NullStatus()

    def describe(self):
        res = super().describe()
        res[self.image.name].update(dict(external="FILESTORE"))
        return res

    def unstage(self):
        super().unstage()
        self._resource_document = None
        self._result.clear()

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item

    def connect(self, sim_type, sim_id):
        sb = SirepoBluesky(self.sirepo_server)
        data, sirepo_schema = sb.auth(sim_type, sim_id)
        self.data = data
        self.sb = sb
        if not self.source_simulation:

            def class_factory(cls_name):
                dd = {k: Cpt(SynAxis) for k in self.parameters}
                return type(cls_name, (Device,), dd)

            sirepo_components = {}

            # Create sirepo component for each optical element, set active element
            # to the one selected by the user
            for i in range(len(data["models"]["beamline"])):
                optic = data["models"]["beamline"][i]["title"]
                optic_id = self.sb.find_optic_id_by_name(optic)

                self.parameters = {f"sirepo_{k}": v for k, v in data["models"]["beamline"][optic_id].items()}

                self.optic_parameters[optic] = self.parameters

                SirepoComponent = class_factory("SirepoComponent")
                sirepo_component = SirepoComponent(name=optic)

                for k, v in self.parameters.items():
                    getattr(sirepo_component, k).set(v)

                sirepo_components[sirepo_component.name] = sirepo_component

            self.sirepo_components = sirepo_components

        else:
            # Create source components
            self.source_parameters = {
                f"sirepo_intensityReport_{k}": v for k, v in data["models"]["intensityReport"].items()
            }

            def source_class_factory(cls_name):
                dd = {k: Cpt(SynAxis) for k in self.source_parameters}
                return type(cls_name, (Device,), dd)

            SirepoComponent = source_class_factory("SirepoComponent")
            self.source_component = SirepoComponent(name="intensityReport")

            for k, v in self.source_parameters.items():
                getattr(self.source_component, k).set(v)

        for k in self.optic_parameters:
            if self.optic_parameters[k]["sirepo_type"] == "watch":
                self.watch_name = self.optic_parameters[k]["sirepo_title"]

    """
    Get list of available sirepo components / parameters / watchpoints
    """

    def view_sirepo_components(self):
        watchpoints = []
        for k in self.optic_parameters:
            print(f"OPTIC:  {k}")
            print(f"PARAMETERS: {self.optic_parameters[k]}")
            if self.optic_parameters[k]["sirepo_type"] == "watch":
                watchpoints.append(k)
        print(f"WATCHPOINTS: {watchpoints}")

    """
    Selects specific optical component for any scan
        - Any parameter selected must be of this component

    Parameters
    ----------
    name : str
        name of optic
    """

    def select_optic(self, name):
        self.sirepo_component = self.sirepo_components[name]

    """
    Returns a parameter based on Ophyd objects created in connect()
        - User can specify any parameter name of the selected component
        - No need to put "sirepo_" before the name

    Parameters
    ----------
    name : str
        name of parameter to create
    """

    def create_parameter(self, name):
        real_name = f"sirepo_{name}"
        ct = 0
        while f"field{ct}" in self.fields.keys():
            ct += 1
        fieldkey = f"field{ct}"
        parentkey = f"par{ct}"

        self.fields[fieldkey] = real_name
        self.parents[parentkey] = self.sirepo_component.name
        key = f"{self.parents[parentkey]}_{name}"
        param = getattr(self.sirepo_component, real_name)
        self.active_parameters[key] = param

        return param

    """
    Sets active watchpoint for the trigger() method

    Parameters
    ----------
    name : str
        name of watchpoint
    """

    def set_watchpoint(self, name):
        self.watch_name = name
