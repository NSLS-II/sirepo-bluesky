from examples.prepare_flyer_env import RE, db, root_dir

import bluesky.plans as bp

import sirepo_bluesky.sirepo_flyer as sf

import time as ttime
from multiprocessing import Process


def multiple_fly(run_scans_parallel=True):
    params_to_change = []
    flyers = []
    for i in range(5):
        key1 = 'Aperture'
        parameters_update1 = {'horizontalSize': (i + 1) * .1, 'verticalSize': (15 - i) * .1}
        key2 = 'Lens'
        parameters_update2 = {'horizontalFocalLength': i + 8}
        key3 = 'Obstacle'
        parameters_update3 = {'horizontalSize': 5 - i}
        params_to_change.append({key1: parameters_update1,
                                 key2: parameters_update2,
                                 key3: parameters_update3})

    for params in params_to_change:
        sim_flyer = sf.SirepoFlyer(sim_id='87XJ4oEb', server_name='http://10.10.10.10:8000',
                                   root_dir=root_dir, params_to_change=[params],
                                   watch_name='W60', run_parallel=False)
        flyers.append(sim_flyer)

    if run_scans_parallel:
        procs = []
        for i in range(len(flyers)):
            p = Process(target=run, args=(flyers[i],))
            p.start()
            procs.append(p)
        # wait for procs to finish
        for p in procs:
            p.join()
    else:
        # run serial
        RE(bp.fly([flyer for flyer in flyers]))


def run(flyer):
    RE(bp.fly([flyer]))


if __name__ == '__main__':
    multiple_fly(run_scans_parallel=True)
