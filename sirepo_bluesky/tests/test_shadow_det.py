import json

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

    RE(bp.count([shadow_det]))

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


@pytest.mark.docker
def test_shadow_detector_docker_beam_stats_report(RE, db, tmpdir):
    _test_shadow_detector(
        RE,
        db,
        tmpdir,
        sim_id="00000002",
        sim_report_type="beam_stats_report",
        server_name="http://localhost:8000",
    )

    hdr = db[-1]
    t = hdr.table()
    assert list(t.columns) == [
        "time",
        "shadow_det_image",
        "shadow_det_mean",
        "shadow_det_photon_energy",
        "shadow_det_beam_statistics_report",
    ]
    beam_statistics_report_str = t["shadow_det_beam_statistics_report"][1]
    assert type(beam_statistics_report_str) is str
    beam_statistics_report = json.loads(beam_statistics_report_str)

    available_fields = [
        "angxpzp",
        "angxz",
        "s",
        "sigdix",
        "sigdiz",
        "sigmax",
        "sigmaxpzp",
        "sigmaxz",
        "sigmaz",
        "x",
        "xp",
        "z",
        "zp",
    ]

    assert set(beam_statistics_report.keys()) == set(available_fields)

    length = 807

    for field in available_fields:
        assert np.array(beam_statistics_report[field]).shape == (length,)

    assert np.allclose(
        np.mean(beam_statistics_report["angxpzp"]), 2.211199214690907e-09
    )
    assert np.allclose(np.mean(beam_statistics_report["angxz"]), 5.808713898817275e-07)
    assert np.allclose(np.mean(beam_statistics_report["s"]), 33.58038661710039)
    assert np.allclose(np.mean(beam_statistics_report["sigdix"]), 0.0011698015394024878)
    assert np.allclose(np.mean(beam_statistics_report["sigdiz"]), 4.214191655245657e-05)
    assert np.allclose(np.mean(beam_statistics_report["sigmax"]), 0.0028331705566906917)
    assert np.allclose(
        np.mean(beam_statistics_report["sigmaxpzp"]), -6.429420083567669e-16
    )
    assert np.allclose(
        np.mean(beam_statistics_report["sigmaxz"]), 6.606042728342832e-09
    )
    assert np.allclose(np.mean(beam_statistics_report["sigmaz"]), 0.0004813342804196106)
    assert np.allclose(np.mean(beam_statistics_report["x"]), -4.613524631932644e-18)
    assert np.allclose(np.mean(beam_statistics_report["xp"]), -5.373988556032905e-19)
    assert np.allclose(np.mean(beam_statistics_report["z"]), -1.4755304204693282e-06)
    assert np.allclose(np.mean(beam_statistics_report["zp"]), 1.0113398478476434e-10)
