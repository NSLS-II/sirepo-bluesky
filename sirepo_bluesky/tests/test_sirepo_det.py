import vcr
import os

from sirepo_bluesky.sirepo_detector import SirepoDetector
import bluesky.plans as bp
import sirepo_bluesky.tests

cassette_location = os.path.join(os.path.dirname(sirepo_bluesky.tests.__file__), 'vcr_cassettes')


@vcr.use_cassette(f'{cassette_location}/test_sirepo_detector.yml')
def test_sirepo_detector(RE, db, tmpdir):
    import datetime
    from ophyd.utils import make_dir_tree

    RE.subscribe(db.insert)

    root_dir = '/tmp/data'
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)

    sirepo_det = SirepoDetector(sim_id='e75qHII6', reg=db.reg)
    sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
    sirepo_det.configuration_attrs = ['horizontal_extent',
                                      'vertical_extent',
                                      'shape']

    RE(bp.count([sirepo_det]))


@vcr.use_cassette(f'{cassette_location}/test_sirepo_det_grid_scan.yml')
def test_sirepo_det_grid_scan(RE, db, tmpdir):
    import datetime
    from ophyd.utils import make_dir_tree

    RE.subscribe(db.insert)

    root_dir = '/tmp/data'
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)

    sirepo_det = SirepoDetector(sim_id='e75qHII6', reg=db.reg)
    sirepo_det.select_optic('Aperture')
    param1 = sirepo_det.create_parameter('horizontalSize')
    param2 = sirepo_det.create_parameter('verticalSize')
    sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
    sirepo_det.configuration_attrs = ['horizontal_extent',
                                      'vertical_extent',
                                      'shape']

    RE(bp.grid_scan([sirepo_det],
                    param1, 0, 1, 3,
                    param2, 0, 1, 3,
                    True))
