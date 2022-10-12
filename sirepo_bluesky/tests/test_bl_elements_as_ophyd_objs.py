import copy
import json
import os
import pprint

import bluesky.plans as bp
import bluesky.plan_stubs as bps
import dictdiffer
import matplotlib.pyplot as plt
import numpy as np
import pytest
import tfs

from sirepo_bluesky.madx_flyer import MADXFlyer
from sirepo_bluesky.sirepo_ophyd import BeamStatisticsReport, create_classes, create_variable_classes


def test_beamline_elements_as_ophyd_objects(srw_tes_simulation):
    classes, objects = create_classes(
        srw_tes_simulation.data, connection=srw_tes_simulation
    )

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(mono_crystal1.summary())  # noqa
    pprint.pprint(mono_crystal1.read())  # noqa


@pytest.mark.parametrize("method", ["set", "put"])
def test_beamline_elements_set_put(srw_tes_simulation, method):
    classes, objects = create_classes(
        srw_tes_simulation.data, connection=srw_tes_simulation
    )
    globals().update(**objects)

    for i, (k, v) in enumerate(objects.items()):
        old_value = v.element_position.get()
        old_sirepo_value = srw_tes_simulation.data["models"]["beamline"][i]["position"]

        getattr(v.element_position, method)(old_value + 100)

        new_value = v.element_position.get()
        new_sirepo_value = srw_tes_simulation.data["models"]["beamline"][i]["position"]

        print(
            f"\n  Changed: {old_value} -> {new_value}\n   Sirepo: {old_sirepo_value} -> {new_sirepo_value}\n"
        )

        assert old_value == old_sirepo_value
        assert new_value == new_sirepo_value
        assert new_value != old_value
        assert abs(new_value - (old_value + 100)) < 1e-8


@pytest.mark.parametrize("method", ["set", "put"])
def test_grazing_angle_calculation(srw_tes_simulation, method):
    classes, objects = create_classes(
        srw_tes_simulation.data, connection=srw_tes_simulation
    )
    globals().update(**objects)

    params_before = copy.deepcopy(toroid.grazingAngle._sirepo_dict)  # noqa F821
    params_before.pop("grazingAngle")

    getattr(toroid.grazingAngle, method)(10)  # noqa F821

    params_after = copy.deepcopy(toroid.grazingAngle._sirepo_dict)  # noqa F821
    params_after.pop("grazingAngle")

    params_diff = list(dictdiffer.diff(params_before, params_after))
    assert len(params_diff) > 0  # should not be empty

    expected_vector_values = {
        "nvx": 0,
        "nvy": 0.9999500004166653,
        "nvz": -0.009999833334166664,
        "tvx": 0,
        "tvy": 0.009999833334166664,
    }

    actual_vector_values = {
        "nvx": toroid.normalVectorX.get(),  # noqa F821
        "nvy": toroid.normalVectorY.get(),  # noqa F821
        "nvz": toroid.normalVectorZ.get(),  # noqa F821
        "tvx": toroid.tangentialVectorX.get(),  # noqa F821
        "tvy": toroid.tangentialVectorY.get(),  # noqa F821
    }

    assert not list(dictdiffer.diff(expected_vector_values, actual_vector_values))


def test_beamline_elements_simple_connection(srw_basic_simulation):
    classes, objects = create_classes(
        srw_basic_simulation.data, connection=srw_basic_simulation
    )

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(watchpoint.summary())  # noqa F821
    pprint.pprint(watchpoint.read())  # noqa F821


def test_shadow_with_run_engine(RE, db, shadow_tes_simulation, num_steps=5):
    classes, objects = create_classes(
        shadow_tes_simulation.data, connection=shadow_tes_simulation
    )
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


def test_beam_statistics_report_only(RE, db, shadow_tes_simulation):
    classes, objects = create_classes(
        shadow_tes_simulation.data, connection=shadow_tes_simulation
    )
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


def test_beam_statistics_report_and_watchpoint(RE, db, shadow_tes_simulation):
    classes, objects = create_classes(
        shadow_tes_simulation.data, connection=shadow_tes_simulation
    )
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
    assert w9_diffs == [
        ("change", ["models", "beamline", 5, "r_maj"], (10000.0, 50000.0))
    ]

    bsr_diffs = list(dictdiffer.diff(bsr_data_1, bsr_data_5))
    assert bsr_diffs == [
        ("change", ["models", "beamline", 5, "r_maj"], (10000.0, 50000.0))
    ]

    w9_bsr_diffs = list(dictdiffer.diff(w9_data_1, bsr_data_5))
    assert w9_bsr_diffs == [
        ("change", ["models", "beamline", 5, "r_maj"], (10000.0, 50000.0)),
        ("change", "report", ("watchpointReport12", "beamStatisticsReport")),
    ]


@pytest.mark.parametrize("method", ["set", "put"])
def test_mad_x_elements_set_put(madx_resr_storage_ring_simulation, method):
    classes, objects = create_classes(
        madx_resr_storage_ring_simulation.data, connection=madx_resr_storage_ring_simulation
    )
    globals().update(**objects)

    for i, (k, v) in enumerate(objects.items()):
        old_value = v.l.get()  # l is length
        old_sirepo_value = madx_resr_storage_ring_simulation.data["models"]["elements"][i]["l"]

        getattr(v.l, method)(old_value + 10)

        new_value = v.l.get()
        new_sirepo_value = madx_resr_storage_ring_simulation.data["models"]["elements"][i]["l"]

        print(
            f"\n  Changed: {old_value} -> {new_value}\n   Sirepo: {old_sirepo_value} -> {new_sirepo_value}\n"
        )

        assert old_value == old_sirepo_value
        assert new_value == new_sirepo_value
        assert new_value != old_value
        assert abs(new_value - (old_value + 10)) < 1e-8


def test_mad_x_elements_simple_connection(madx_bl2_tdc_simulation):
    classes, objects = create_classes(
        madx_bl2_tdc_simulation.data, connection=madx_bl2_tdc_simulation
    )

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(bpm5.summary())  # noqa
    pprint.pprint(bpm5.read())  # noqa


def test_madx_with_run_engine(RE, db, madx_bl2_tdc_simulation):
    classes, objects = create_classes(
        madx_bl2_tdc_simulation.data, connection=madx_bl2_tdc_simulation
    )
    globals().update(**objects)

    madx_flyer = MADXFlyer(connection=madx_bl2_tdc_simulation,
                           root_dir="/tmp/sirepo-bluesky-data",
                           report="elementAnimation250-20")

    (uid,) = RE(bp.fly([madx_flyer]))  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(stream_name="madx_flyer", fill=True)
    print(tbl)

    resource_files = []
    for name, doc in hdr.documents():
        if name == "resource":
            resource_files.append(os.path.join(doc["root"], doc["resource_path"]))

    # Check that we have only one resource madx file for all datum documents:
    assert len(set(resource_files)) == 1

    df = tfs.read(resource_files[0])
    for column in df.columns:
        if column == "NAME":
            assert (tbl[f"madx_flyer_{column}"].astype("string").values == df[column].values).all()
        else:
            assert np.allclose(np.array(tbl[f"madx_flyer_{column}"]).astype(float), np.array(df[column]))


def test_madx_variables_with_run_engine(RE, db, madx_bl2_tdc_simulation):
    classes, objects = create_classes(
        madx_bl2_tdc_simulation.data, connection=madx_bl2_tdc_simulation
    )

    classes_var, objects_var = create_variable_classes(
        madx_bl2_tdc_simulation.data, connection=madx_bl2_tdc_simulation
    )
    globals().update(**objects)

    madx_flyer = MADXFlyer(connection=madx_bl2_tdc_simulation,
                           root_dir="/tmp/sirepo-bluesky-data",
                           report="elementAnimation250-20")

    def madx_plan(parameter="ihq1", value=2.0):
        yield from bps.mv(objects_var[parameter].value, value)
        return (yield from bp.fly([madx_flyer]))

    (uid,) = RE(madx_plan())  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(stream_name="madx_flyer", fill=True)
    print(tbl)

    S = [0.2, 1.34, 4.76, 5.9, 7.4, 8.54, 10.1405, 12.91425,
         19.47205, 20.58655, 21.38655, 22.24655, 23.10655,
         23.10655, 24.10655, 25.01655, 25.14655, 25.40055,
         25.88155, 26.88155, 29.92205]
    BETX = [1.04080000e+01, 2.23630865e+01, 5.45490503e+01, 6.85639797e+01,
            8.95080711e+01, 3.07485642e+02, 1.48819798e+01, 4.01917445e+02,
            8.76888193e+01, 1.72370137e+02, 2.04524432e+02, 1.22838562e+01,
            5.31960299e+01, 5.31960299e+01, 4.15143523e+01, 3.39923407e-02,
            6.42294261e-01, 6.54463047e+00, 3.12227617e+01, 1.23493229e+02,
            2.78859359e-02]
    BETY = [1.04080000e+01, 3.89622295e+00, 2.29735786e+01, 4.91159086e+01,
            9.85840248e+01, 5.81731898e+00, 7.01313899e+01, 7.34896758e+01,
            2.01619048e+02, 8.91117598e+01, 9.45050916e+00, 1.70765137e+00,
            3.19775219e+01, 3.19775219e+01, 5.35173761e+01, 5.06793788e+00,
            2.34217363e+00, 4.32283940e-02, 7.17054244e+00, 7.55144928e+01,
            2.00861311e+00]

    assert np.allclose(np.array(tbl["madx_flyer_S"]).astype(float), S)
    assert np.allclose(np.array(tbl["madx_flyer_BETX"]).astype(float), BETX)
    assert np.allclose(np.array(tbl["madx_flyer_BETY"]).astype(float), BETY)
