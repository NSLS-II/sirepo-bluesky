import asyncio
from bluesky.run_engine import RunEngine, TransitionError
from bluesky.callbacks import best_effort
import databroker
from databroker import Broker
from sirepo_bluesky.srw_handler import SRWFileHandler
import numpy as np
import os
import pytest

@pytest.fixture(scope='function')
def RE(request):
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    RE = RunEngine({}, loop=loop)

    bec = best_effort.BestEffortCallback()
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