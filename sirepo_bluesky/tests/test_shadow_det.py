import bluesky.plans as bp
import numpy as np
import pytest

from sirepo_bluesky.shadow_detector import SirepoShadowDetector


def _test_shadow_detector(RE, db, tmpdir, sim_id, server_name, sim_report_type):
    import datetime

    from ophyd.utils import make_dir_tree

    root_dir = tmpdir / "data"
    _ = make_dir_tree(datetime.datetime.now().year, base_path=str(root_dir))

    shadow_det = SirepoShadowDetector(
        name="shadow_det",
        sim_report_type=sim_report_type,
        sim_id=sim_id,
        sirepo_server=server_name,
        root_dir=str(root_dir),
    )
    shadow_det.select_optic("Aperture")
    shadow_det.create_parameter("horizontalSize")
    shadow_det.create_parameter("verticalSize")
    shadow_det.read_attrs = ["image", "mean", "photon_energy"]
    shadow_det.configuration_attrs = ["horizontal_extent", "vertical_extent", "shape"]

    shadow_det.active_parameters["Aperture_horizontalSize"].set(1.0)
    shadow_det.active_parameters["Aperture_verticalSize"].set(1.0)

    shadow_det.duration.kind = "hinted"

    (uid,) = RE(bp.count([shadow_det]))

    # Check that the duration for each step in the simulation is positive:
    sim_durations = np.array(db[uid].table()["shadow_det_duration"])
    assert (sim_durations > 0.0).all()

    return shadow_det


@pytest.mark.docker
def test_shadow_detector_docker_default_report(RE, db, tmpdir):
    _test_shadow_detector(
        RE,
        db,
        tmpdir,
        sim_id="00000001",
        sim_report_type="default_report",
        server_name="http://localhost:8000",
    )
    hdr = db[-1]
    t = hdr.table()
    mean = t.iloc[0]["shadow_det_mean"]

    assert mean == 9.7523, "incorrect mean value from bp.count"
