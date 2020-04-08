import requests
import time
import random
import numconv
import hashlib
import base64
import numpy as np


class SirepoBluesky(object):
    """
    Invoke a remote sirepo simulation with custom arguments.

    Parameters
    ----------
    server: str
        Sirepo server to call, ex. 'http://locahost:8000'

    Examples
    --------
    # sim_id is the last section from the simulation url
    # e.g., '.../1tNWph0M'
    sim_id = '1tNWph0M'
    sb = SirepoBluesky('http://localhost:8000')
    data, schema = sb.auth('srw', sim_id)
    # update the model values and choose the report
    data['models']['undulator']['verticalAmplitude'] = 0.95
    data['report'] = 'trajectoryReport'
    sb.run_simulation()
    f = sb.get_datafile()

    # assumes there is an aperture named A1 and a watchpoint named W1 in the beamline
    aperture = sb.find_element(data['models']['beamline'], 'title', 'A1')
    aperture['horizontalSize'] = 0.1
    aperture['verticalSize'] = 0.1
    watch = sb.find_element(data['models']['beamline'], 'title', 'W1')
    data['report'] = 'watchpointReport{}'.format(watch['id'])
    sb.run_simulation()
    f2 = sb.get_datafile()

    Start Sirepo Server
    -------------------
    $ SIREPO_BLUESKY_AUTH_SECRET=bluesky sirepo service http
    - 'bluesky' is the secret key in this case

    """

    def __init__(self, server, secret='bluesky'):
        self.server = server
        self.secret = secret

    def auth(self, sim_type, sim_id):
        """ Connect to the server and returns the data for the simulation identified by sim_id. """
        req = dict(simulationType=sim_type, simulationId=sim_id)
        r = random.SystemRandom()
        req['authNonce'] = str(int(time.time())) + '-' + ''.join(r.choice(numconv.BASE62) for x in range(32))
        h = hashlib.sha256()
        h.update(':'.join([req['authNonce'], req['simulationType'],
                           req['simulationId'], self.secret]).encode())
        req['authHash'] = 'v1:' + base64.urlsafe_b64encode(h.digest()).decode()

        self.cookies = None
        res = self._post_json('bluesky-auth', req)
        assert 'state' in res and res['state'] == 'ok', 'bluesky_auth failed: {}'.format(res)
        self.sim_type = sim_type
        self.sim_id = sim_id
        self.schema = res['schema']
        self.data = res['data']
        return self.data, self.schema

    def copy_sim(self, sim_name):
        """ Create a copy of the current simulation. Returns a new instance of SirepoBluesky. """
        assert self.sim_id
        # simulationId, simulationType, name, folder
        res = self._post_json('copy-simulation', {
            'simulationId': self.sim_id,
            'simulationType': self.sim_type,
            'folder': self.data['models']['simulation']['folder'],
            'name': sim_name,
        })
        copy = SirepoBluesky(self.server, self.secret)
        copy.cookies = self.cookies
        copy.sim_type = self.sim_type
        copy.sim_id = res['models']['simulation']['simulationId']
        copy.schema = self.schema
        copy.data = res
        copy.is_copy = True
        return copy

    def delete_copy(self):
        """ Delete a simulation which was created using copy_sim(). """
        assert self.is_copy
        res = self._post_json('delete-simulation', {
            'simulationId': self.sim_id,
            'simulationType': self.sim_type,
        })
        assert res['state'] == 'ok'
        self.sim_id = None

    @staticmethod
    def find_element(elements, field, value):
        """ Helper method to lookup an element in an array by field value. """
        for e in elements:
            if e[field] == value:
                return e
        assert False, 'element not found, {}={}'.format(field, value)

    def find_optic_id_by_name(self, optic_name):
        """ Return optic element from simulation data. """
        for optic_id in range(len(self.data['models']['beamline'])):
            if self.data['models']['beamline'][optic_id]['title'] == optic_name:
                return optic_id
        raise ValueError(f'Not valid optic {optic_name}')

    def get_datafile(self):
        """ Request the raw datafile of simulation results from the server.

            Notes
            -----
            Call auth() and run_simulation() before this.
        """
        assert hasattr(self, 'cookies'), 'call auth() before get_datafile()'
        url = 'download-data-file/{}/{}/{}/-1'.format(self.sim_type, self.sim_id, self.data['report'])
        response = requests.get('{}/{}'.format(self.server, url), cookies=self.cookies)
        self._assert_success(response, url)
        return response.content

    @staticmethod
    def update_grazing_vectors(data_to_update, grazing_vectors_params):
        """Update grazing angle vectors"""
        grazing_params = {}
        grazing_angle = grazing_vectors_params['angle']
        nvx = nvy = np.sqrt(1 - np.sin(grazing_angle / 1000) ** 2)
        tvx = tvy = np.sqrt(1 - np.cos(grazing_angle / 1000) ** 2)
        nvz = -tvx
        if grazing_vectors_params['autocompute_type'] == 'horizontal':
            nvy = tvy = 0
        elif grazing_vectors_params['autocompute_type'] == 'vertical':
            nvx = tvx = 0
        grazing_params['normalVectorX'] = nvx
        grazing_params['normalVectorY'] = nvy
        grazing_params['tangentialVectorX'] = tvx
        grazing_params['tangentialVectorY'] = tvy
        grazing_params['normalVectorZ'] = nvz
        data_to_update.update(grazing_params)

    def run_simulation(self, max_status_calls=1000):
        """ Run the sirepo simulation and returns the formatted plot data.

        Parameters
        ----------
        max_status_calls: int, optional
            Maximum calls to check a running simulation's status. Roughly in seconds.
            Default is 1000.

        """
        assert hasattr(self, 'cookies'), 'call auth() before run_simulation()'
        assert 'report' in self.data, 'client needs to set data[\'report\']'
        self.data['simulationId'] = self.sim_id
        res = self._post_json('run-simulation', self.data)
        for _ in range(max_status_calls):
            state = res['state']
            if state == 'completed' or state == 'error':
                break
            time.sleep(res['nextRequestSeconds'])
            res = self._post_json('run-status', res['nextRequest'])
        assert state == 'completed', 'simulation failed to completed: {}'.format(state)
        return res

    @staticmethod
    def _assert_success(response, url):
        assert response.status_code == requests.codes.ok,\
            '{} request failed, status: {}'.format(url, response.status_code)

    def _post_json(self, url, payload):
        response = requests.post('{}/{}'.format(self.server, url), json=payload, cookies=self.cookies)
        self._assert_success(response, url)
        if not self.cookies:
            self.cookies = response.cookies
        return response.json()
