import json

import pytest

from sirepo_bluesky.shadow_detector import SirepoShadowDetector
import bluesky.plans as bp


def _test_shadow_detector(RE, db, tmpdir, sim_id, server_name, sim_report_type):
    import datetime
    from ophyd.utils import make_dir_tree

    RE.subscribe(db.insert)

    root_dir = tmpdir / "data"
    _ = make_dir_tree(datetime.datetime.now().year, base_path=str(root_dir))

    shadow_det = SirepoShadowDetector(
        name="shadow_det", sim_report_type=sim_report_type,
        sim_id=sim_id, sirepo_server=server_name, root_dir=str(root_dir)
    )
    shadow_det.select_optic('Aperture')
    shadow_det.create_parameter('horizontalSize')
    shadow_det.create_parameter('verticalSize')
    shadow_det.read_attrs = ['image', 'mean', 'photon_energy']
    shadow_det.configuration_attrs = ['horizontal_extent',
                                      'vertical_extent',
                                      'shape']

    shadow_det.active_parameters['Aperture_horizontalSize'].set(1.0)
    shadow_det.active_parameters['Aperture_verticalSize'].set(1.0)

    RE(bp.count([shadow_det]))

    return shadow_det


@pytest.mark.docker
def test_shadow_detector_docker_default_report(RE, db, tmpdir):
    _test_shadow_detector(RE, db, tmpdir,
                          sim_id='00000001',
                          sim_report_type="default_report",
                          server_name='http://localhost:8000')
    hdr = db[-1]
    t = hdr.table()
    mean = t.iloc[0]['shadow_det_mean']

    assert mean == 9.7523, "incorrect mean value from bp.count"


@pytest.mark.docker
def test_shadow_detector_docker_beam_stats_report(RE, db, tmpdir):
    _test_shadow_detector(
        RE, db, tmpdir,
        sim_id='00000001',
        sim_report_type="beam_stats_report",
        server_name='http://localhost:8000')

    hdr = db[-1]
    t = hdr.table()
    assert list(t.columns) == [
        'time', 'shadow_det_image', 'shadow_det_mean', 'shadow_det_photon_energy', 'shadow_det_beam_statistics_report'
    ]
    beam_statistics_report_str = t['shadow_det_beam_statistics_report'][1]
    assert type(beam_statistics_report_str) is str
    beam_statistics_report = json.loads(beam_statistics_report_str)
    assert beam_statistics_report[0] == {'isRotated': False, 'matrix': [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]], 's': 0.0, 'sigdix': 5.4812999999999996e-08, 'sigdiz': 5.4812999999999996e-08, 'sigma_mx': [[0.0004, 0.0, 0.0, 0.0], [0.0, 3.0044649689999995e-15, 0.0, 0.0], [0.0, 0.0, 0.0004, 0.0], [0.0, 0.0, 0.0, 3.0044649689999995e-15]], 'sigmax': 0.0002, 'sigmaz': 0.0002, 'x': 0.0, 'xp': 0.0, 'z': 0.0, 'zp': 0.0}
