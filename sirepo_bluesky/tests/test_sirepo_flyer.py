import os

import pytest
import vcr

from sirepo_bluesky.sirepo_bluesky import SirepoBluesky
from sirepo_bluesky.sirepo_flyer import SirepoFlyer
import bluesky.plans as bp
import sirepo_bluesky.tests

cassette_location = os.path.join(os.path.dirname(sirepo_bluesky.tests.__file__), 'vcr_cassettes')


def _test_smoke_sirepo(sim_id, server_name):
    sb = SirepoBluesky(server_name)
    data, schema = sb.auth('srw', sim_id)
    assert 'beamline' in data['models']


@vcr.use_cassette(f'{cassette_location}/test_smoke_sirepo.yml')
def test_smoke_sirepo_vcr():
    _test_smoke_sirepo(sim_id='87XJ4oEb',
                       server_name='http://10.10.10.10:8000')


@pytest.mark.docker
def test_smoke_sirepo_docker():
    _test_smoke_sirepo(sim_id='00000000',
                       server_name='http://localhost:8000')


def _test_sirepo_flyer(RE_no_plot, db, tmpdir, sim_id, server_name):
    import datetime
    from ophyd.utils import make_dir_tree

    RE_no_plot.subscribe(db.insert)

    root_dir = f'{tmpdir}/sirepo_flyer_data'
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)

    params_to_change = []
    for i in range(1, 6):
        key1 = 'Aperture'
        parameters_update1 = {'horizontalSize': i * .1, 'verticalSize': (16 - i) * .1}
        key2 = 'Lens'
        parameters_update2 = {'horizontalFocalLength': i + 7}
        key3 = 'Obstacle'
        parameters_update3 = {'horizontalSize': 6 - i}
        params_to_change.append({key1: parameters_update1,
                                 key2: parameters_update2,
                                 key3: parameters_update3})

    sirepo_flyer = SirepoFlyer(sim_id=sim_id, server_name=server_name,
                               root_dir=root_dir, params_to_change=params_to_change,
                               watch_name='W60', run_parallel=False)

    RE_no_plot(bp.fly([sirepo_flyer]))

    hdr = db[-1]
    t = hdr.table(stream_name='sirepo_flyer')
    db_means = []
    actual_means = [36779651609602.38,
                    99449330615601.89,
                    149289119385413.34,
                    223428480785808.78,
                    388594677365777.9]
    for i in range(len(t)):
        db_means.append(t.iloc[i]['sirepo_flyer_mean'])

    assert set(actual_means) == set(db_means), "fly scan means do not match actual means"


@vcr.use_cassette(f'{cassette_location}/test_sirepo_flyer.yml')
def test_sirepo_flyer_vcr(RE_no_plot, db, tmpdir):
    _test_sirepo_flyer(RE_no_plot, db, tmpdir,
                       sim_id='87XJ4oEb',
                       server_name='http://10.10.10.10:8000')


@pytest.mark.docker
def test_sirepo_flyer_docker(RE_no_plot, db, tmpdir):
    _test_sirepo_flyer(RE_no_plot, db, tmpdir,
                       sim_id='00000000',
                       server_name='http://localhost:8000')
