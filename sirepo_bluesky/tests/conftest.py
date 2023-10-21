import asyncio
import datetime

import databroker
import pytest
from bluesky.callbacks import best_effort
from bluesky.run_engine import RunEngine
from databroker import Broker
from ophyd.utils import make_dir_tree

from sirepo_bluesky.common.sirepo_client import SirepoClient
from sirepo_bluesky.madx.madx_handler import MADXFileHandler
from sirepo_bluesky.shadow.shadow_handler import ShadowFileHandler
from sirepo_bluesky.srw.srw_handler import SRWFileHandler, SRWHDF5FileHandler

DEFAULT_SIREPO_URL = "http://localhost:8000"


@pytest.fixture(scope="function")
def db():
    """Return a data broker"""
    # MongoDB backend:
    db = Broker.named("local")  # mongodb backend
    try:
        databroker.assets.utils.install_sentinels(db.reg.config, version=1)
    except Exception:
        pass

    db.reg.register_handler("srw", SRWFileHandler, overwrite=True)
    db.reg.register_handler("SIREPO_FLYER", SRWFileHandler, overwrite=True)
    db.reg.register_handler("SRW_HDF5", SRWHDF5FileHandler, overwrite=True)
    db.reg.register_handler("shadow", ShadowFileHandler, overwrite=True)
    db.reg.register_handler("madx", MADXFileHandler, overwrite=True)

    return db


@pytest.fixture(scope="function")
def RE(db):
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    RE = RunEngine({}, loop=loop)
    RE.subscribe(db.insert)

    bec = best_effort.BestEffortCallback()
    RE.subscribe(bec)

    return RE


@pytest.fixture(scope="function")
def RE_no_plot(db):
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    RE = RunEngine({}, loop=loop)
    RE.subscribe(db.insert)

    bec = best_effort.BestEffortCallback()
    bec.disable_plots()
    RE.subscribe(bec)

    return RE


@pytest.fixture(scope="function")
def make_dirs():
    root_dir = "/tmp/sirepo-bluesky-data"
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)


@pytest.fixture(scope="function")
def srw_empty_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("srw", "emptysim")
    return connection


@pytest.fixture(scope="function")
def srw_youngs_double_slit_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("srw", "00000000")
    return connection


@pytest.fixture(scope="function")
def srw_basic_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("srw", "00000001")
    return connection


@pytest.fixture(scope="function")
def srw_tes_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("srw", "00000002")
    return connection


@pytest.fixture(scope="function")
def srw_ari_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("srw", "00000003")
    return connection


@pytest.fixture(scope="function")
def srw_chx_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("srw", "HXV1JQ5c")
    return connection


@pytest.fixture(scope="function")
def shadow_basic_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("shadow", "00000001")
    return connection


@pytest.fixture(scope="function")
def shadow_tes_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("shadow", "00000002")
    return connection


@pytest.fixture(scope="function")
def madx_resr_storage_ring_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("madx", "00000000")
    return connection


@pytest.fixture(scope="function")
def madx_bl1_compton_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("madx", "00000001")
    return connection


@pytest.fixture(scope="function")
def madx_bl2_triplet_tdc_simulation(make_dirs):
    connection = SirepoClient(DEFAULT_SIREPO_URL)
    data, _ = connection.auth("madx", "00000002")
    return connection
