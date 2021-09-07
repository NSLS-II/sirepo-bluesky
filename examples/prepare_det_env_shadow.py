import datetime
import json  # noqa F401

import databroker
import matplotlib.pyplot as plt
import numpy as np  # noqa F401
from bluesky.callbacks import best_effort
from bluesky.run_engine import RunEngine
from databroker import Broker
from ophyd.utils import make_dir_tree

from sirepo_bluesky.shadow_handler import ShadowFileHandler

RE = RunEngine({})
bec = best_effort.BestEffortCallback()
RE.subscribe(bec)

# MongoDB backend:
db = Broker.named('local')  # mongodb backend
try:
    databroker.assets.utils.install_sentinels(db.reg.config, version=1)
except Exception:
    pass

RE.subscribe(db.insert)
db.reg.register_handler('shadow', ShadowFileHandler, overwrite=True)

plt.ion()

root_dir = '/tmp/shadow_det_data'
_ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)
