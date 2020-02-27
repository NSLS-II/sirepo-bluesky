import vcr

from ..sirepo_bluesky import SirepoBluesky


# @vcr.use_cassette('./vcr_cassettes/test_smoke_sirepo.yml')
def test_smoke_sirepo():
    sim_id = '87XJ4oEb'
    sb = SirepoBluesky('http://10.10.10.10:8000')
    data, schema = sb.auth('srw', sim_id)
    assert 'beamline' in data['models']


# @vcr.use_cassette('./vcr_cassettes/test_sirepo_flyer.yml')
def test_sirepo_flyer():
    from ..re_config import RE, ROOT_DIR  # , db
    from ..sirepo_flyer import SirepoFlyer
    import bluesky.plans as bp
    params_to_change = []
    for i in range(1, 5 + 1):
        key1 = 'Aperture'
        parameters_update1 = {'horizontalSize': i * .1, 'verticalSize': (6 - i) * .1}
        key2 = 'Lens'
        parameters_update2 = {'horizontalFocalLength': i + 10}

        params_to_change.append({key1: parameters_update1,
                                 key2: parameters_update2})

    sirepo_flyer = SirepoFlyer(sim_id='87XJ4oEb', server_name='http://10.10.10.10:8000',
                               root_dir=ROOT_DIR, params_to_change=params_to_change,
                               watch_name='W60', run_parallel=False)

    RE(bp.fly([sirepo_flyer]))
