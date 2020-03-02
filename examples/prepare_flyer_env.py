import datetime

from bluesky.run_engine import RunEngine
from bluesky.callbacks import best_effort

import databroker
from databroker import Broker

from ophyd.utils import make_dir_tree

from sirepo_bluesky.srw_handler import SRWFileHandler


RE = RunEngine({})
bec = best_effort.BestEffortCallback()
bec.disable_plots()
RE.subscribe(bec)

# MongoDB backend:
db = Broker.named('local')  # mongodb backend
try:
    databroker.assets.utils.install_sentinels(db.reg.config, version=1)
except Exception:
    pass

RE.subscribe(db.insert)
db.reg.register_handler('srw', SRWFileHandler, overwrite=True)
db.reg.register_handler('SIREPO_FLYER', SRWFileHandler, overwrite=True)

root_dir = '/tmp/sirepo_flyer_data'
_ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)
