import asyncio

import databroker
import pytest
from bluesky.callbacks import best_effort
from bluesky.run_engine import RunEngine
from databroker import Broker

import sirepo_bluesky.srw_detector as sd
from sirepo_bluesky.srw_handler import SRWFileHandler


@pytest.fixture(scope='function')
def RE(request):
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    RE = RunEngine({}, loop=loop)

    bec = best_effort.BestEffortCallback()
    RE.subscribe(bec)
    return RE


@pytest.fixture(scope='function')
def RE_no_plot(request):
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    RE = RunEngine({}, loop=loop)

    bec = best_effort.BestEffortCallback()
    bec.disable_plots()
    RE.subscribe(bec)
    return RE


@pytest.fixture(scope='function')
def db(request):
    """Return a data broker
    """
    # MongoDB backend:
    db = Broker.named('local')  # mongodb backend
    try:
        databroker.assets.utils.install_sentinels(db.reg.config, version=1)
    except Exception:
        pass

    db.reg.register_handler('srw', SRWFileHandler, overwrite=True)
    db.reg.register_handler('SIREPO_FLYER', SRWFileHandler, overwrite=True)
    return db


@pytest.fixture(scope='function')
def tes_simulation():
    simulation = sd.SirepoSRWDetector(
        sim_type="srw",
        sim_id="00000002",
        sirepo_server="http://localhost:8000",
        watch_name="W9",
    )
    return simulation
