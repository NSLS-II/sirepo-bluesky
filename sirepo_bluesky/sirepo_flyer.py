import datetime
import hashlib
import os
import time as ttime
from collections import deque
from multiprocessing import Process, Manager
from pathlib import Path

from ophyd.sim import NullStatus, new_uid

from .sirepo_bluesky import SirepoBluesky
from sirepo_bluesky.srw_handler import read_srw_file


class BlueskyFlyer:
    def __init__(self):
        self.name = 'bluesky_flyer'
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


class SirepoFlyer(BlueskyFlyer):
    """
    Multiprocessing "flyer" for Sirepo simulations

    Parameters
    ----------
    sim_id : str
        Simulation ID corresponding to Sirepo simulation being run on local server
    server_name : str
        Address that identifies access to local Sirepo server
    params_to_change : list of dicts of dicts
        List of dictionaries with string optic element names for keys and values that are dictionaries
        with string optic element parameter names for keys and new positions as values

        Example: [{'Aperture': {'horizontalSize': 1, 'verticalSize':2},
                   'Lens': {'horizontalFocalLength': 10}},
                  {'Aperture': {'horizontalSize': 3, 'verticalSize':6},
                   'Lens': {'horizontalFocalLength': 15}}]
    root_dir : str
        Root directory for DataBroker to store data from simulations
    sim_code : str, optional
        Simulation code
    watch_name : str, optional
        The name of the watchpoint viewing the simulation
    run_parallel : bool
        States whether the user want to run flyer using multiprocessing or serially

    Examples
    --------
    if __name__ == '__main__':
        %run -i examples/prepare_flyer_env.py
        import bluesky.plans as bp
        from sirepo_bluesky import sirepo_flyer as sf

        params_to_change = []
        for i in range(1, 5+1):
            key1 = 'Aperture'
            parameters_update1 = {'horizontalSize': i * .1, 'verticalSize': (6 - i) * .1}
            key2 = 'Lens'
            parameters_update2 = {'horizontalFocalLength': i + 10}

            params_to_change.append({key1: parameters_update1,
                                     key2: parameters_update2})

        sirepo_flyer = sf.SirepoFlyer(sim_id='87XJ4oEb', server_name='http://10.10.10.10:8000',
                                      root_dir=root_dir, params_to_change=params_to_change,
                                      watch_name='W60')

        RE(bp.fly([sirepo_flyer]))
    """
    def __init__(self, sim_id, server_name, params_to_change, root_dir, sim_code='srw',
                 watch_name='Watchpoint', run_parallel=True):
        super().__init__()
        self.name = 'sirepo_flyer'
        self._sim_id = sim_id
        self._server_name = server_name
        self._params_to_change = params_to_change
        self._root_dir = root_dir
        self._sim_code = sim_code
        self._copy_count = len(self.params_to_change)
        self._watch_name = watch_name
        self._run_parallel = run_parallel
        self.return_status = {}
        self._copies = None
        self._srw_files = None
        self.procs = None

    def __repr__(self):
        return (f'{self.name} with sim_code="{self._sim_code}" and '
                f'sim_id="{self._sim_id}" at {self._server_name}')

    @property
    def sim_id(self):
        return self._sim_id

    @sim_id.setter
    def sim_id(self, value):
        self._sim_id = value

    @property
    def server_name(self):
        return self._server_name

    @server_name.setter
    def server_name(self, value):
        self._server_name = value

    @property
    def params_to_change(self):
        return self._params_to_change

    @params_to_change.setter
    def params_to_change(self, value):
        self._params_to_change = value

    @property
    def root_dir(self):
        return self._root_dir

    @root_dir.setter
    def root_dir(self, value):
        if not os.path.isdir(value):
            raise ValueError(f"directory named {value} not found")
        self._root_dir = value

    @property
    def sim_code(self):
        return self._sim_code

    @sim_code.setter
    def sim_code(self, value):
        self._sim_code = value

    @property
    def copy_count(self):
        return self._copy_count

    @copy_count.setter
    def copy_count(self, value):
        try:
            value = int(value)
        except TypeError:
            raise
        self._copy_count = value

    @property
    def watch_name(self):
        return self._watch_name

    @watch_name.setter
    def watch_name(self, value):
        self._watch_name = value

    @property
    def run_parallel(self):
        return self._run_parallel

    @run_parallel.setter
    def run_parallel(self, value):
        if isinstance(value, bool):
            self._run_parallel = value
        else:
            raise TypeError(f'invalid type: {type(value)}. Must be boolean')

    def kickoff(self):
        sb = SirepoBluesky(self.server_name)
        data, schema = sb.auth(self.sim_code, self.sim_id)
        self._copies = []
        self._srw_files = []
        autocompute_data = {}
        # grazing angle; check params_to_change
        for component in data['models']['beamline']:
            if 'autocomputeVectors' in component.keys():
                autocompute_data[component['title']] = component['autocomputeVectors']
        update_grazing_vecs_list = []
        for i in self.params_to_change:
            grazing_vecs_dict = {}
            for elem, param in i.items():
                for param_name, val in param.items():
                    if elem in autocompute_data.keys() and param_name == 'grazingAngle':
                        grazing_vecs_dict[elem] = {'angle': val, 'autocompute_type': autocompute_data[elem]}
            update_grazing_vecs_list.append(grazing_vecs_dict)

        for i in range(self._copy_count):
            datum_id = new_uid()
            date = datetime.datetime.now()
            srw_file = str(Path(self.root_dir) / Path(date.strftime('%Y/%m/%d')) / Path('{}.dat'.format(datum_id)))
            self._srw_files.append(srw_file)
            _resource_uid = new_uid()
            resource = {'spec': 'SIREPO_FLYER',
                        'root': self.root_dir,  # from 00-startup.py (added by mrakitin for future generations :D)
                        'resource_path': srw_file,
                        'resource_kwargs': {},
                        'path_semantics': {'posix': 'posix', 'nt': 'windows'}[os.name],
                        'uid': _resource_uid}
            self._resource_uids.append(_resource_uid)
            self._asset_docs_cache.append(('resource', resource))

        for i in range(len(self.params_to_change)):
            # name doesn't need to be unique, server will rename it
            c1 = sb.copy_sim('{} Bluesky'.format(sb.data['models']['simulation']['name']), )
            print('copy {}, {}'.format(c1.sim_id, c1.data['models']['simulation']['name']))

            for key, parameters_to_update in self.params_to_change[i].items():
                optic_id = sb.find_optic_id_by_name(key)
                c1.data['models']['beamline'][optic_id].update(parameters_to_update)
                # update vectors if needed
                if key in update_grazing_vecs_list[i]:
                    sb.update_grazing_vectors(c1.data['models']['beamline'][optic_id],
                                              update_grazing_vecs_list[i][key])
            watch = sb.find_element(c1.data['models']['beamline'], 'title', self.watch_name)
            c1.data['report'] = 'watchpointReport{}'.format(watch['id'])
            self._copies.append(c1)

        if self.run_parallel:
            manager = Manager()
            self.return_status = manager.dict()
            self.procs = []
            for i in range(self.copy_count):
                p = Process(target=self._run, args=(self._copies[i], self.return_status))
                p.start()
                self.procs.append(p)
            # wait for procs to finish
            # for p in self.procs:
            #     p.join()
        else:
            # run serial
            for i in range(self.copy_count):
                print(f'running sim: {self._copies[i].sim_id}')
                status = self._copies[i].run_simulation()
                print(f"Status of sim {self._copies[i].sim_id}: {status['state']}")
                self.return_status[self._copies[i].sim_id] = status['state']
        return NullStatus()

    def complete(self, *args, **kwargs):
        if self.run_parallel:
            for p in self.procs:
                p.join()
        for i in range(len(self._copies)):
            datum_id = self._resource_uids[i]
            datum = {'resource': self._resource_uids[i],
                     'datum_kwargs': {},
                     'datum_id': datum_id}
            self._asset_docs_cache.append(('datum', datum))
            self._datum_ids.append(datum_id)
        return NullStatus()

    def describe_collect(self):
        return_dict = {self.name:
                       {f'{self.name}_image': {'source': f'{self.name}_image',
                                               'dtype': 'array',
                                               'shape': [-1, -1],
                                               'external': 'FILESTORE:'},
                        f'{self.name}_shape': {'source': f'{self.name}_shape',
                                               'dtype': 'array',
                                               'shape': [2]},
                        f'{self.name}_mean': {'source': f'{self.name}_mean',
                                              'dtype': 'number',
                                              'shape': []},
                        f'{self.name}_photon_energy': {'source': f'{self.name}_photon_energy',
                                                       'dtype': 'number',
                                                       'shape': []},
                        f'{self.name}_horizontal_extent': {'source': f'{self.name}_horizontal_extent',
                                                           'dtype': 'array',
                                                           'shape': [2]},
                        f'{self.name}_vertical_extent': {'source': f'{self.name}_vertical_extent',
                                                         'dtype': 'array',
                                                         'shape': [2]},
                        f'{self.name}_hash_value': {'source': f'{self.name}_hash_value',
                                                    'dtype': 'string',
                                                    'shape': []},
                        f'{self.name}_status': {'source': f'{self.name}_status',
                                                'dtype': 'string',
                                                'shape': []},
                        }
                       }
        elem_name = []
        curr_param = []
        for inputs in self.params_to_change:
            for key, params in inputs.items():
                elem_name.append(key)
                curr_param.append(list(params.keys()))

        for i in range(len(elem_name)):
            for j in range(len(curr_param[i])):
                return_dict[self.name].update({f'{self.name}_{elem_name[i]}_{curr_param[i][j]}': {
                    'source': f'{self.name}_{elem_name[i]}_{curr_param[i][j]}',
                    'dtype': 'number',
                    'shape': []}})
        return return_dict

    def collect(self):
        # get results and clean up the copied simulations
        shapes = []
        means = []
        photon_energies = []
        horizontal_extents = []
        vertical_extents = []
        hash_values = []
        for i in range(len(self._copies)):
            data_file = self._copies[i].get_datafile()
            with open(self._srw_files[i], 'wb') as f:
                f.write(data_file)

            ret = read_srw_file(self._srw_files[i])
            means.append(ret['mean'])
            shapes.append(ret['shape'])
            photon_energies.append(ret['photon_energy'])
            horizontal_extents.append(ret['horizontal_extent'])
            vertical_extents.append(ret['vertical_extent'])
            hash_values.append(hashlib.md5(data_file).hexdigest())

            print(f'copy {self._copies[i].sim_id} data hash: {hash_values[i]}')
            self._copies[i].delete_copy()

        statuses = []
        for sim, status in self.return_status.items():
            statuses.append(status)

        assert len(self._copies) == len(self._datum_ids), \
            f'len(self._copies) != len(self._datum_ids) ({len(self._copies)} != {len(self._datum_ids)})'

        now = ttime.time()
        for i, datum_id in enumerate(self._datum_ids):
            elem_name = []
            curr_param = []
            data = {f'{self.name}_image': datum_id,
                    f'{self.name}_shape': shapes[i],
                    f'{self.name}_mean': means[i],
                    f'{self.name}_photon_energy': photon_energies[i],
                    f'{self.name}_horizontal_extent': horizontal_extents[i],
                    f'{self.name}_vertical_extent': vertical_extents[i],
                    f'{self.name}_hash_value': hash_values[i],
                    f'{self.name}_status': statuses[i],
                    }
            for inputs in self.params_to_change:
                for key, params in inputs.items():
                    elem_name.append(key)
                    curr_param.append(list(params.keys()))
            for ii in range(len(elem_name)):
                for jj in range(len(curr_param[ii])):
                    data[f'{self.name}_{elem_name[ii]}_{curr_param[ii][jj]}'] = \
                        self.params_to_change[i][elem_name[ii]][curr_param[ii][jj]]

            yield {'data': data,
                   'timestamps': {key: now for key in data},
                   'time': now,
                   'filled': {key: False for key in data}}

    @staticmethod
    def _run(sim, return_status):
        """ Run simulations using multiprocessing. """
        print(f'running sim {sim.sim_id}')
        status = sim.run_simulation()
        print(f"Status of sim {sim.sim_id}: {status['state']}")
        return_status[sim.sim_id] = status['state']
