import json
import os

import bluesky.plans as bp
import dictdiffer
import matplotlib.pyplot as plt
import numpy as np
import pytest

from sirepo_bluesky.shadow.shadow_handler import BeamStatisticsReport, create_classes


@pytest.mark.shadow
def test_shadow_with_run_engine(RE, db, shadow_tes_simulation, num_steps=5):
    classes, objects = create_classes(connection=shadow_tes_simulation)
    globals().update(**objects)

    aperture.horizontalSize.kind = "hinted"  # noqa F821

    (uid,) = RE(bp.scan([w9], aperture.horizontalSize, 0, 2, num_steps))  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(fill=True)
    print(tbl)

    # Check that the duration for each step in the simulation is positive:
    sim_durations = np.array(tbl["w9_duration"])
    assert (sim_durations > 0.0).all()

    w9_image = np.array(list(hdr.data("w9_image")))
    # Check the shape of the image data is right:
    assert w9_image.shape == (num_steps, 100, 100)

    w9_mean_from_image = w9_image.mean(axis=(1, 2))
    w9_mean_from_table = np.array(tbl["w9_mean"])

    # Check the number of elements correspond to a number of scan points:
    assert len(w9_mean_from_table) == num_steps

    # Check that an average values of the first and last images are right:
    assert np.allclose(w9_image[0].mean(), 0.0)
    assert np.allclose(w9_image[-1].mean(), 0.255665516042795)

    # Check that the values from the table and averages from the image data are
    # the same:
    assert np.allclose(w9_mean_from_table, w9_mean_from_image)

    # Check that the averaged intensities from the table are ascending:
    assert np.all(np.diff(w9_mean_from_table) > 0)

    resource_files = []
    for name, doc in hdr.documents():
        if name == "resource":
            resource_files.append(os.path.basename(doc["resource_path"]))

    # Check that all resource files are unique:
    assert len(set(resource_files)) == num_steps


@pytest.mark.shadow
def test_beam_statistics_report_only(RE, db, shadow_tes_simulation):
    classes, objects = create_classes(connection=shadow_tes_simulation)
    globals().update(**objects)

    bsr = BeamStatisticsReport(name="bsr", connection=shadow_tes_simulation)

    toroid.r_maj.kind = "hinted"  # noqa F821

    scan_range = (10_000, 50_000, 21)

    (uid,) = RE(bp.scan([bsr], toroid.r_maj, *scan_range))  # noqa F821
    hdr = db[uid]
    tbl = hdr.table()
    print(tbl)

    calc_durations = np.array(tbl["time"].diff(), dtype=float)[1:] / 1e9
    print(f"Calculated durations (seconds): {calc_durations}")

    # Check that the duration for each step in the simulation is non-zero:
    cpt_durations = np.array(tbl["bsr_duration"])
    print(f"Durations from component (seconds): {cpt_durations}")

    assert (cpt_durations > 0.0).all()
    assert (calc_durations > cpt_durations[1:]).all()

    fig = plt.figure()
    ax = fig.add_subplot()
    ax.plot(np.linspace(*scan_range)[1:], calc_durations)
    ax.set_ylabel("Duration of simulations [s]")
    ax.set_xlabel("Torus Major Radius [m]")
    title = (
        f"Shadow TES simulation\n"
        f"RE(bp.scan([bsr], toroid.r_maj, "
        f"{', '.join([str(x) for x in scan_range])}))"
    )
    ax.set_title(title)
    fig.savefig("TES-Shadow-timing.png")
    # plt.show()


@pytest.mark.shadow
def test_beam_statistics_report_and_watchpoint(RE, db, shadow_tes_simulation):
    classes, objects = create_classes(connection=shadow_tes_simulation)
    globals().update(**objects)

    bsr = BeamStatisticsReport(name="bsr", connection=shadow_tes_simulation)

    toroid.r_maj.kind = "hinted"  # noqa F821

    (uid,) = RE(bp.scan([bsr, w9], toroid.r_maj, 10000, 50000, 5))  # noqa F821
    hdr = db[uid]
    tbl = hdr.table()
    print(tbl)

    w9_data_1 = json.loads(tbl["w9_sirepo_data_json"][1])
    w9_data_5 = json.loads(tbl["w9_sirepo_data_json"][5])

    bsr_data_1 = json.loads(tbl["bsr_sirepo_data_json"][1])
    bsr_data_5 = json.loads(tbl["bsr_sirepo_data_json"][5])

    w9_diffs = list(dictdiffer.diff(w9_data_1, w9_data_5))
    assert w9_diffs == [("change", ["models", "beamline", 5, "r_maj"], (10000.0, 50000.0))]

    bsr_diffs = list(dictdiffer.diff(bsr_data_1, bsr_data_5))
    assert bsr_diffs == [("change", ["models", "beamline", 5, "r_maj"], (10000.0, 50000.0))]

    w9_bsr_diffs = list(dictdiffer.diff(w9_data_1, bsr_data_5))
    assert w9_bsr_diffs == [
        ("change", ["models", "beamline", 5, "r_maj"], (10000.0, 50000.0)),
        ("change", "report", ("watchpointReport12", "beamStatisticsReport")),
    ]
