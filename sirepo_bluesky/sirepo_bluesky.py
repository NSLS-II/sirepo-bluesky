import base64
import hashlib
import random
import time

import numconv
import numpy as np
import requests


class SirepoBlueskyClientException(Exception):
    pass


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

    def __init__(self, server, secret="bluesky"):
        self.server = server
        self.secret = secret

    def auth(self, sim_type, sim_id):
        """Connect to the server and returns the data for the simulation identified by sim_id."""
        req = dict(simulationType=sim_type, simulationId=sim_id)
        r = random.SystemRandom()
        req["authNonce"] = str(int(time.time())) + "-" + "".join(r.choice(numconv.BASE62) for x in range(32))
        h = hashlib.sha256()
        h.update(
            ":".join(
                [
                    req["authNonce"],
                    req["simulationType"],
                    req["simulationId"],
                    self.secret,
                ]
            ).encode()
        )
        req["authHash"] = "v1:" + base64.urlsafe_b64encode(h.digest()).decode()

        self.cookies = None
        res = self._post_json("auth-bluesky-login", req)
        if not ("state" in res and res["state"] == "ok"):
            raise SirepoBlueskyClientException(f"bluesky_auth failed: {res}")
        self.sim_type = sim_type
        self.sim_id = sim_id
        self.schema = res["schema"]
        self.data = res["data"]
        return self.data, self.schema

    def copy_sim(self, sim_name):
        """Create a copy of the current simulation. Returns a new instance of SirepoBluesky."""
        if not self.sim_id:
            raise ValueError(f"sim_id is {self.sim_id!r}")
        res = self._post_json(
            "copy-simulation",
            {
                "simulationId": self.sim_id,
                "simulationType": self.sim_type,
                "folder": self.data["models"]["simulation"]["folder"],
                "name": sim_name,
            },
        )
        copy = SirepoBluesky(self.server, self.secret)
        copy.cookies = self.cookies
        copy.sim_type = self.sim_type
        copy.sim_id = res["models"]["simulation"]["simulationId"]
        copy.schema = self.schema
        copy.data = res
        copy.is_copy = True
        return copy

    def delete_copy(self):
        """Delete a simulation which was created using copy_sim()."""
        if not self.is_copy:
            raise ValueError("This simulation is not a copy")
        res = self._post_json(
            "delete-simulation",
            {
                "simulationId": self.sim_id,
                "simulationType": self.sim_type,
            },
        )
        if not res["state"] == "ok":
            raise SirepoBlueskyClientException(f"Could not delete simulation: {res}")
        self.sim_id = None

    def compute_grazing_orientation(self, optical_element):
        res = self._post_json(
            "stateless-compute",
            {
                "method": "compute_grazing_orientation",
                "optical_element": optical_element,
                "simulationId": self.sim_id,
                "simulationType": self.sim_type,
            },
        )
        return res

    @staticmethod
    def find_element(elements, field, value):
        """Helper method to lookup an element in an array by field value."""
        for e in elements:
            if e[field] == value:
                return e
        raise ValueError(f"element not found, {field}={value}")

    def find_optic_id_by_name(self, optic_name):
        """Return optic element from simulation data."""
        for optic_id in range(len(self.data["models"]["beamline"])):
            if self.data["models"]["beamline"][optic_id]["title"] == optic_name:
                return optic_id
        raise ValueError(f"Not valid optic {optic_name}")

    def get_datafile(self, file_index=-1):
        """Request the raw datafile of simulation results from the server.

        Notes
        -----
        Call auth() and run_simulation() before this.
        """
        if not hasattr(self, "cookies"):
            raise Exception("must call auth() before get_datafile()")
        url = f"download-data-file/{self.sim_type}/{self.sim_id}/{self.data['report']}/{file_index}"
        response = requests.get(f"{self.server}/{url}", cookies=self.cookies)
        self._assert_success(response, url)
        return response.content

    def simulation_list(self):
        """Returns a list of simulations for the authenticated user."""
        return self._post_json("simulation-list", dict(simulationType=self.sim_type))

    @staticmethod
    def update_grazing_vectors(data_to_update, grazing_vectors_params):
        """Update grazing angle vectors"""
        grazing_params = {}
        grazing_angle = grazing_vectors_params["angle"]
        nvx = nvy = np.sqrt(1 - np.sin(grazing_angle / 1000) ** 2)
        tvx = tvy = np.sqrt(1 - np.cos(grazing_angle / 1000) ** 2)
        nvz = -tvx
        if grazing_vectors_params["autocompute_type"] == "horizontal":
            nvy = tvy = 0
        elif grazing_vectors_params["autocompute_type"] == "vertical":
            nvx = tvx = 0
        grazing_params["normalVectorX"] = nvx
        grazing_params["normalVectorY"] = nvy
        grazing_params["tangentialVectorX"] = tvx
        grazing_params["tangentialVectorY"] = tvy
        grazing_params["normalVectorZ"] = nvz
        data_to_update.update(grazing_params)

    def run_simulation(self, max_status_calls=1000):
        """Run the sirepo simulation and returns the formatted plot data.

        Parameters
        ----------
        max_status_calls: int, optional
            Maximum calls to check a running simulation's status. Roughly in seconds.
            Default is 1000.

        """
        start_time = time.monotonic()
        if not hasattr(self, "cookies"):
            raise Exception("call auth() before run_simulation()")
        if "report" not in self.data:
            raise Exception("client needs to set data['report']")
        self.data["simulationId"] = self.sim_id
        self.data["forceRun"] = True
        res = self._post_json("run-simulation", self.data)
        for _ in range(max_status_calls):
            state = res["state"]
            if state == "completed" or state == "error":
                break
            if "nextRequestSeconds" not in res:
                raise Exception(f'missing "nextRequestSeconds" in response: {res}')
            time.sleep(res["nextRequestSeconds"])
            res = self._post_json("run-status", res["nextRequest"])
        if not state == "completed":
            raise SirepoBlueskyClientException(f"simulation failed to complete: {state}")
        return res, time.monotonic() - start_time

    @staticmethod
    def _assert_success(response, url):
        if not response.status_code == requests.codes.ok:
            raise SirepoBlueskyClientException(f"{url} request failed, status: {response.status_code}")

    def _post_json(self, url, payload):
        response = requests.post(f"{self.server}/{url}", json=payload, cookies=self.cookies)
        self._assert_success(response, url)
        if not self.cookies:
            self.cookies = response.cookies
        return response.json()
