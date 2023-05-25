import os

import bluesky.plans as bp
import numpy as np
import pytest
import vcr

import sirepo_bluesky.tests
from sirepo_bluesky.srw_detector import SirepoSRWDetector

cassette_location = os.path.join(os.path.dirname(sirepo_bluesky.tests.__file__), "vcr_cassettes")


def _test_srw_detector(RE, db, tmpdir, sim_type, sim_id, server_name):
    import datetime

    from ophyd.utils import make_dir_tree

    root_dir = "/tmp/sirepo-bluesky-data"
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)

    srw_det = SirepoSRWDetector(
        name="srw_det",
        sim_type=sim_type,
        sim_id=sim_id,
        sirepo_server=server_name,
        root_dir=root_dir,
    )
    srw_det.select_optic("Aperture")
    srw_det.create_parameter("horizontalSize")
    srw_det.create_parameter("verticalSize")
    srw_det.read_attrs = ["image", "mean", "photon_energy"]
    srw_det.configuration_attrs = ["horizontal_extent", "vertical_extent", "shape"]

    srw_det.active_parameters["Aperture_horizontalSize"].set(1.0)
    srw_det.active_parameters["Aperture_verticalSize"].set(1.0)

    srw_det.duration.kind = "hinted"

    RE(bp.count([srw_det]))

    hdr = db[-1]
    t = hdr.table()
    mean = t.iloc[0]["srw_det_mean"]

    assert mean == 1334615738479247.2, "incorrect mean value from bp.count"

    sim_durations = np.array(t["srw_det_duration"])
    assert (sim_durations > 0.0).all()


@vcr.use_cassette(f"{cassette_location}/test_srw_detector.yml")
def test_srw_detector_vcr(RE, db, tmpdir):
    _test_srw_detector(
        RE,
        db,
        tmpdir,
        sim_type="srw",
        sim_id="00000001",
        server_name="http://localhost:8000",
    )


@pytest.mark.docker
def test_srw_detector_docker(RE, db, tmpdir):
    _test_srw_detector(
        RE,
        db,
        tmpdir,
        sim_type="srw",
        sim_id="00000001",
        server_name="http://localhost:8000",
    )


def _test_srw_det_grid_scan(RE, db, tmpdir, sim_type, sim_id, server_name):
    import datetime

    from ophyd.utils import make_dir_tree

    root_dir = "/tmp/sirepo-bluesky-data"
    _ = make_dir_tree(datetime.datetime.now().year, base_path=root_dir)

    srw_det = SirepoSRWDetector(
        name="srw_det",
        sim_type=sim_type,
        sim_id=sim_id,
        sirepo_server=server_name,
        root_dir=root_dir,
    )
    srw_det.select_optic("Aperture")
    param1 = srw_det.create_parameter("horizontalSize")
    param2 = srw_det.create_parameter("verticalSize")
    srw_det.read_attrs = ["image", "mean", "photon_energy"]
    srw_det.configuration_attrs = ["horizontal_extent", "vertical_extent", "shape"]

    RE(bp.grid_scan([srw_det], param1, 0, 1, 3, param2, 0, 1, 3, True))

    db_means = []
    actual_means = [
        0,
        0,
        0,
        1334615738479247.2,
        1208898410914477.0,
        0,
        0,
        1208898410914477.0,
        1334615738479247.2,
    ]

    hdr = db[-1]
    t = hdr.table()
    for i in range(len(t)):
        db_means.append(t.iloc[i]["srw_det_mean"])
    assert actual_means == db_means, "grid_scan means do not match actual means"


@vcr.use_cassette(f"{cassette_location}/test_srw_det_grid_scan.yml")
def test_srw_det_grid_scan_vcr(RE, db, tmpdir):
    _test_srw_det_grid_scan(
        RE,
        db,
        tmpdir,
        sim_type="srw",
        sim_id="00000001",
        server_name="http://localhost:8000",
    )


@pytest.mark.docker
def test_srw_det_grid_scan_docker(RE, db, tmpdir):
    _test_srw_det_grid_scan(
        RE,
        db,
        tmpdir,
        sim_type="srw",
        sim_id="00000001",
        server_name="http://localhost:8000",
    )
