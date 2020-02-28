import vcr
import os

from sirepo_bluesky.sirepo_bluesky import SirepoBluesky
from sirepo_bluesky.sirepo_flyer import SirepoFlyer
import bluesky.plans as bp
import sirepo_bluesky.tests

cassette_location = os.path.join(os.path.dirname(sirepo_bluesky.tests.__file__), 'vcr_cassettes')


@vcr.use_cassette(f'{cassette_location}/test_smoke_sirepo.yml')
def test_smoke_sirepo():
    sim_id = '87XJ4oEb'
    sb = SirepoBluesky('http://10.10.10.10:8000')
    data, schema = sb.auth('srw', sim_id)
    assert 'beamline' in data['models']


@vcr.use_cassette(f'{cassette_location}/test_sirepo_flyer.yml')
def test_sirepo_flyer(RE_no_plot, db, tmpdir):
    import datetime
    from ophyd.utils import make_dir_tree

    RE_no_plot.subscribe(db.insert)

    root_dir = f'{tmpdir}/sirepo_flyer_data'
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)

    params_to_change = []
    for i in range(1, 5 + 1):
        key1 = 'Aperture'
        parameters_update1 = {'horizontalSize': i * .1, 'verticalSize': (6 - i) * .1}
        key2 = 'Lens'
        parameters_update2 = {'horizontalFocalLength': i + 10}

        params_to_change.append({key1: parameters_update1,
                                 key2: parameters_update2})

    sirepo_flyer = SirepoFlyer(sim_id='87XJ4oEb', server_name='http://10.10.10.10:8000',
                               root_dir=root_dir, params_to_change=params_to_change,
                               watch_name='W60', run_parallel=False)

    RE_no_plot(bp.fly([sirepo_flyer]))
