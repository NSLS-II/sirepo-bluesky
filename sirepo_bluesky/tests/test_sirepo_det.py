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
    sirepo_det.select_optic('Aperture')
    sirepo_det.create_parameter('horizontalSize')
    sirepo_det.create_parameter('verticalSize')
    sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
    sirepo_det.configuration_attrs = ['horizontal_extent',
                                      'vertical_extent',
                                      'shape']

    sirepo_det.active_parameters['Aperture_horizontalSize'].set(1.0)
    sirepo_det.active_parameters['Aperture_verticalSize'].set(1.0)

    RE(bp.count([sirepo_det]))

    hdr = db[-1]
    t = hdr.table()
    mean = t.iloc[0]['sirepo_det_mean']

    assert mean == 1334615738479247.2, "incorrect mean value from bp.count"


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

    db_means = []
    actual_means = [0,
                    0,
                    0,
                    1334615738479247.2,
                    1208898410914477.0,
                    0,
                    0,
                    1208898410914477.0,
                    1334615738479247.2]

    hdr = db[-1]
    t = hdr.table()
    for i in range(len(t)):
        db_means.append(t.iloc[i]['sirepo_det_mean'])
    assert actual_means == db_means, "grid_scan means do not match actual means"
