from collections import deque
import datetime
from pathlib import Path

import unyt as u

from event_model import compose_resource

from ophyd import Device, Signal, Component as Cpt
from ophyd.sim import SynAxis, NullStatus, new_uid

from .srw_handler import read_srw_file
from .sirepo_bluesky import SirepoBluesky


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


class SirepoDetector(Device):
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
    mean = Cpt(Signal)
    photon_energy = Cpt(Signal)
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)

    def __init__(self, name='sirepo_det', sim_id=None, watch_name=None,
                 sirepo_server='http://10.10.10.10:8000', source_simulation=False, **kwargs):
        super().__init__(name=name, **kwargs)
        self._asset_docs_cache = deque()
        self._resource_document = None
        self._datum_factory = None

        self.sirepo_component = None
        self.fields = {}
        self.field_units = {}
        self.parents = {}
        self._result = {}
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
        self.one_d_reports = ['intensityReport']
        self.two_d_reports = ['watchpointReport']
        assert sim_id, 'Simulation ID must be provided. Currently it is set to {}'.format(sim_id)
        self.connect(sim_id=self._sim_id)

    @property
    def hints(self):
        if self._hints is None:
            return {'fields': [self.mean.name]}
        return self._hints

    @hints.setter
    def hints(self, val):
        self._hints = dict(val)

    def update_value(self, value, units):
        unyt_obj = u.m
        starting_unit = value * unyt_obj
        converted_unit = starting_unit.to(units)
        return converted_unit

    """
    Get new parameter values from Sirepo server

    """
    def update_parameters(self):
        data, sirepo_schema = self.sb.auth('srw', self._sim_id)
        self.data = data
        for key, value in self.sirepo_components.items():
            optic_id = self.sb.find_optic_id_by_name(key)
            self.parameters = {f'sirepo_{k}': v for k, v in
                               data['models']['beamline'][optic_id].items()}
            for k, v in self.parameters.items():
                getattr(value, k).set(v)

    def trigger(self):
        super().trigger()

        date = datetime.datetime.now()
        file_name = new_uid()
        self._resource_document, self._datum_factory, _ = compose_resource(
            start={'uid': 'needed for compose_resource() but will be discarded'},
            spec='srw',
            root='/tmp/data',
            resource_path=str(Path(date.strftime('%Y/%m/%d')) / Path('{}.dat'.format(file_name))),
            # ndim is not known yet, it will be established at the end of this method
            resource_kwargs={'ndim': 0}
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop('run_start')
        self._asset_docs_cache.append(('resource', self._resource_document))

        srw_file = Path(self._resource_document['root']) / Path(self._resource_document['resource_path'])

        if not self.source_simulation:
            if self.sirepo_component is not None:
                for component in self.data['models']['beamline']:
                    if 'autocomputeVectors' in component.keys():
                        self.autocompute_params[component['title']] = component['autocomputeVectors']
                for i in range(len(self.active_parameters)):
                    real_field = self.fields['field' + str(i)].replace('sirepo_', '')
                    dict_key = self.fields['field' + str(i)].replace('sirepo', self.parents['par' + str(i)])
                    x = self.active_parameters[dict_key].read()[
                        f'{self.parents["par" + str(i)]}_{self.fields["field" + str(i)]}']['value']
                    element = self.sb.find_element(self.data['models']['beamline'],
                                                   'title',
                                                   self.parents['par' + str(i)])
                    element[real_field] = x
                    if self.parents[f'par{i}'] in self.autocompute_params.keys() and 'grazingAngle' in dict_key:
                        grazing_vecs_dict = {}
                        autocompute_key = f'{self.parents[f"par{i}"]}_sirepo_autocomputeVectors'
                        autocompute_type = self.sirepo_components[self.parents[f'par{i}']].read()[
                            autocompute_key]['value']
                        grazing_vecs_dict['angle'] = x
                        grazing_vecs_dict['autocompute_type'] = autocompute_type
                        optic_id = self.sb.find_optic_id_by_name(self.parents[f'par{i}'])
                        self.sb.update_grazing_vectors(self.data['models']['beamline'][optic_id],
                                                       grazing_vecs_dict)

                watch = self.sb.find_element(self.data['models']['beamline'],
                                             'title',
                                             self.watch_name)
                self.data['report'] = 'watchpointReport{}'.format(watch['id'])

        else:
            self.data['report'] = "intensityReport"
        self.sb.run_simulation()

        with open(srw_file, 'wb') as f:
            f.write(self.sb.get_datafile())

        if self.data['report'] in self.one_d_reports:
            ndim = 1
        else:
            ndim = 2
        ret = read_srw_file(srw_file, ndim=ndim)

        # ndim has now been established, add it to the resource document
        self._resource_document["resource_kwargs"]["ndim"] = ndim
        datum_document = self._datum_factory(datum_kwargs={})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])
        self.shape.put(ret['shape'])
        self.mean.put(ret['mean'])
        self.photon_energy.put(ret['photon_energy'])
        self.horizontal_extent.put(ret['horizontal_extent'])
        self.vertical_extent.put(ret['vertical_extent'])

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
        self._result.clear()

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item

    def connect(self, sim_id):
        sb = SirepoBluesky(self.sirepo_server)
        data, sirepo_schema = sb.auth('srw', sim_id)
        self.data = data
        self.sb = sb
        if not self.source_simulation:

            def class_factory(cls_name):
                dd = {k: Cpt(SynAxis) for k in self.parameters}
                return type(cls_name, (Device,), dd)

            sirepo_components = {}

            # Create sirepo component for each optical element, set active element
            # to the one selected by the user
            for i in range(len(data['models']['beamline'])):
                optic = (data['models']['beamline'][i]['title'])
                optic_id = self.sb.find_optic_id_by_name(optic)

                self.parameters = {f'sirepo_{k}': v for k, v in
                                   data['models']['beamline'][optic_id].items()}

                self.optic_parameters[optic] = self.parameters

                SirepoComponent = class_factory('SirepoComponent')
                sirepo_component = SirepoComponent(name=optic)

                for k, v in self.parameters.items():
                    getattr(sirepo_component, k).set(v)

                sirepo_components[sirepo_component.name] = sirepo_component

            self.sirepo_components = sirepo_components

        else:
            # Create source components
            self.source_parameters = {f'sirepo_intensityReport_{k}': v for k, v in
                                      data['models']['intensityReport'].items()}

            def source_class_factory(cls_name):
                dd = {k: Cpt(SynAxis) for k in self.source_parameters}
                return type(cls_name, (Device,), dd)

            SirepoComponent = source_class_factory('SirepoComponent')
            self.source_component = SirepoComponent(name='intensityReport')

            for k, v in self.source_parameters.items():
                getattr(self.source_component, k).set(v)

        for k in self.optic_parameters:
            if self.optic_parameters[k]['sirepo_type'] == 'watch':
                self.watch_name = self.optic_parameters[k]['sirepo_title']

    """
    Get list of available sirepo components / parameters / watchpoints
    """
    def view_sirepo_components(self):
        watchpoints = []
        for k in self.optic_parameters:
            print(f'OPTIC:  {k}')
            print(f'PARAMETERS: {self.optic_parameters[k]}')
            if self.optic_parameters[k]['sirepo_type'] == 'watch':
                watchpoints.append(k)
        print(f'WATCHPOINTS: {watchpoints}')

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
        while f'field{ct}' in self.fields.keys():
            ct += 1
        fieldkey = f'field{ct}'
        parentkey = f'par{ct}'

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

    """

    How to run beamline library example
    -----------------------------------
    %run -i examples/prepare_det_env.py
    import bluesky.plans as bp
    import bluesky.plan_stubs as bps
    import sirepo_bluesky.sirepo_detector as sd
    sirepo_det = sd.SirepoDetector(sim_id='qyQ4yILz', reg=db.reg)
    sirepo_det.select_optic('Aperture')
    param1 = sirepo_det.create_parameter('horizontalSize')
    param2 = sirepo_det.create_parameter('verticalSize')
    sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
    sirepo_det.configuration_attrs = ['horizontal_extent',
                                      'vertical_extent',
                                      'shape']

    Grid scan
    ---------
    RE(bp.grid_scan([sirepo_det],
                    param1, 0, 1, 10,
                    param2, 0, 1, 10,
                    True))

    1D scan
    -------
    RE(bps.mov(param2, 1))
    RE(bp.scan([sirepo_det], param1, 0, 1, 10))

    count
    -----
    RE(bp.count([sirepo_det]))


    How to run source page example
    ------------------------------
    %run -i examples/prepare_det_env.py
    import bluesky.plans as bp
    import sirepo_bluesky.sirepo_detector as sd
    sirepo_det = sd.SirepoDetector(sim_id='8GJJWLFh', reg=db.reg, source_simulation=True)
    sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
    sirepo_det.configuration_attrs = ['horizontal_extent', 'vertical_extent', 'shape']

    RE(bp.count([sirepo_det]))

    To see image:
    -------------
    hdr = db[-1]
    imgs = list(hdr.data('sirepo_det_image'))
    plt.plot(imgs[-1])

    """
