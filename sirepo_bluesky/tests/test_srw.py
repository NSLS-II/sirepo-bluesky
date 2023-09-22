import copy
import json
import os
import pprint

import bluesky.plans as bp
import dictdiffer
import matplotlib.pyplot as plt
import numpy as np
import peakutils
import pytest

from sirepo_bluesky.common import create_classes


@pytest.mark.srw
def test_beamline_elements_as_ophyd_objects(srw_tes_simulation):
    classes, objects = create_classes(connection=srw_tes_simulation)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(mono_crystal1.summary())  # noqa
    pprint.pprint(mono_crystal1.read())  # noqa


@pytest.mark.srw
def test_empty_simulation(srw_empty_simulation):
    classes, objects = create_classes(connection=srw_empty_simulation)
    globals().update(**objects)

    assert not srw_empty_simulation.data["models"]["beamline"]
    objects.pop("post_propagation")
    assert not objects


@pytest.mark.srw
@pytest.mark.parametrize("method", ["set", "put"])
def test_beamline_elements_set_put(srw_tes_simulation, method):
    classes, objects = create_classes(connection=srw_tes_simulation)
    globals().update(**objects)

    i = 0
    for k, v in objects.items():
        if "element_position" in v.component_names:
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
            i += 1


@pytest.mark.srw
@pytest.mark.parametrize("method", ["set", "put"])
def test_crl_calculation(srw_chx_simulation, method):
    classes, objects = create_classes(connection=srw_chx_simulation)
    globals().update(**objects)

    params_before = copy.deepcopy(crl1.tipRadius._sirepo_dict)  # noqa F821
    params_before.pop("tipRadius")

    getattr(crl1.tipRadius, method)(2000)  # noqa F821

    params_after = copy.deepcopy(crl1.tipRadius._sirepo_dict)  # noqa F821
    params_after.pop("tipRadius")

    params_diff = list(dictdiffer.diff(params_before, params_after))
    assert len(params_diff) > 0  # should not be empty

    expected_values = {
        "absoluteFocusPosition": -6.195573642892285,
        "focalDistance": 237.666984823537,
    }

    actual_values = {
        "absoluteFocusPosition": crl1.absoluteFocusPosition.get(),  # noqa F821
        "focalDistance": crl1.focalDistance.get(),  # noqa F821
    }

    assert not list(dictdiffer.diff(expected_values, actual_values))


@pytest.mark.srw
@pytest.mark.parametrize("method", ["set", "put"])
def test_crystal_calculation(srw_tes_simulation, method):
    classes, objects = create_classes(connection=srw_tes_simulation)
    globals().update(**objects)

    params_before = copy.deepcopy(mono_crystal1.energy._sirepo_dict)  # noqa F821
    params_before.pop("energy")

    getattr(mono_crystal1.energy, method)(2000)  # noqa F821

    params_after = copy.deepcopy(mono_crystal1.energy._sirepo_dict)  # noqa F821
    params_after.pop("energy")

    params_diff = list(dictdiffer.diff(params_before, params_after))
    assert len(params_diff) > 0  # should not be empty

    expected_values = {
        "dSpacing": 3.1355713563754857,
        "grazingAngle": 1419.9107955732711,
        "nvx": 0,
        "nvy": 0.15031366142760424,
        "nvz": -0.9886383581412506,
        "outframevx": 1.0,
        "outframevy": 0.0,
        "outoptvx": 0.0,
        "outoptvy": 0.29721170287997256,
        "outoptvz": -0.9548116063764552,
        "psi0i": 6.530421915581681e-05,
        "psi0r": -0.00020558072555357544,
        "psiHBi": 4.559368494529194e-05,
        "psiHBr": -0.00010207663788071082,
        "psiHi": 4.559368494529194e-05,
        "psiHr": -0.00010207663788071082,
        "tvx": 0,
        "tvy": 0.9886383581412506,
    }

    actual_values = {
        "dSpacing": mono_crystal1.dSpacing.get(),  # noqa F821
        "grazingAngle": mono_crystal1.grazingAngle.get(),  # noqa F821
        "nvx": mono_crystal1.nvx.get(),  # noqa F821
        "nvy": mono_crystal1.nvy.get(),  # noqa F821
        "nvz": mono_crystal1.nvz.get(),  # noqa F821
        "outframevx": mono_crystal1.outframevx.get(),  # noqa F821
        "outframevy": mono_crystal1.outframevy.get(),  # noqa F821
        "outoptvx": mono_crystal1.outoptvx.get(),  # noqa F821
        "outoptvy": mono_crystal1.outoptvy.get(),  # noqa F821
        "outoptvz": mono_crystal1.outoptvz.get(),  # noqa F821
        "psi0i": mono_crystal1.psi0i.get(),  # noqa F821
        "psi0r": mono_crystal1.psi0r.get(),  # noqa F821
        "psiHBi": mono_crystal1.psiHBi.get(),  # noqa F821
        "psiHBr": mono_crystal1.psiHBr.get(),  # noqa F821
        "psiHi": mono_crystal1.psiHi.get(),  # noqa F821
        "psiHr": mono_crystal1.psiHr.get(),  # noqa F821
        "tvx": mono_crystal1.tvx.get(),  # noqa F821
        "tvy": mono_crystal1.tvy.get(),  # noqa F821
    }

    assert not list(dictdiffer.diff(expected_values, actual_values))


@pytest.mark.srw
@pytest.mark.parametrize("method", ["set", "put"])
def test_grazing_angle_calculation(srw_tes_simulation, method):
    classes, objects = create_classes(connection=srw_tes_simulation)
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


@pytest.mark.srw
def test_beamline_elements_simple_connection(srw_basic_simulation):
    classes, objects = create_classes(connection=srw_basic_simulation)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(watchpoint.summary())  # noqa F821
    pprint.pprint(watchpoint.read())  # noqa F821


@pytest.mark.srw
def test_srw_source_with_run_engine(RE, db, srw_ari_simulation, num_steps=5):
    classes, objects = create_classes(
        connection=srw_ari_simulation,
        extra_model_fields=["undulator", "intensityReport"],
    )
    globals().update(**objects)

    undulator.verticalAmplitude.kind = "hinted"  # noqa F821

    single_electron_spectrum.initialEnergy.get()  # noqa F821
    single_electron_spectrum.initialEnergy.put(20)  # noqa F821
    single_electron_spectrum.finalEnergy.put(1100)  # noqa F821

    assert srw_ari_simulation.data["models"]["intensityReport"]["initialEnergy"] == 20
    assert srw_ari_simulation.data["models"]["intensityReport"]["finalEnergy"] == 1100

    (uid,) = RE(
        bp.scan(
            [single_electron_spectrum],  # noqa F821
            undulator.verticalAmplitude,  # noqa F821
            0.2,
            1,
            num_steps,
        )
    )  # noqa F821

    hdr = db[uid]
    tbl = hdr.table()
    print(tbl)

    ses_data = np.array(list(hdr.data("single_electron_spectrum_image")))
    ampl_data = np.array(list(hdr.data("undulator_verticalAmplitude")))
    # Check the shape of the image data is right:
    assert ses_data.shape == (num_steps, 2000)

    resource_files = []
    for name, doc in hdr.documents():
        if name == "resource":
            resource_files.append(os.path.basename(doc["resource_path"]))

    # Check that all resource files are unique:
    assert len(set(resource_files)) == num_steps

    fig = plt.figure()
    ax = fig.add_subplot()
    for i in range(num_steps):
        ax.plot(ses_data[i, :], label=f"vert. magn. fld. {ampl_data[i]:.3f}T")
        peak = peakutils.indexes(ses_data[i, :])
        ax.scatter(peak, ses_data[i, peak])
    ax.grid()
    ax.legend()
    ax.set_title("Single-Electron Spectrum vs. Vertical Magnetic Field")
    fig.savefig("ses-vs-ampl.png")
    # plt.show()


@pytest.mark.srw
def test_srw_propagation_with_run_engine(RE, db, srw_chx_simulation, num_steps=5):
    classes, objects = create_classes(connection=srw_chx_simulation)
    globals().update(**objects)

    post_propagation.hrange_mod.kind = "hinted"  # noqa F821

    (uid,) = RE(bp.scan([sample], post_propagation.hrange_mod, 0.1, 0.3, num_steps))  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(fill=True)
    print(tbl)

    # Check that the duration for each step in the simulation is positive:
    sim_durations = np.array(tbl["sample_duration"])
    assert (sim_durations > 0.0).all(), "Simulation steps did not properly run."

    sample_image = []
    for i in range(num_steps):
        sample_image.append(np.array(list(hdr.data("sample_image"))[i]))

    # Check the shape of the image data is right and that hrange_mod was properly changed:
    for i, hrange_mod in enumerate(np.linspace(0.1, 0.3, num_steps)):
        assert json.loads(tbl["sample_sirepo_data_json"][i + 1])["models"]["postPropagation"][5] == hrange_mod


@pytest.mark.srw
def test_srw_tes_propagation_with_run_engine(RE, db, srw_tes_simulation, num_steps=5):
    classes, objects = create_classes(connection=srw_tes_simulation)
    globals().update(**objects)

    post_propagation.hrange_mod.kind = "hinted"  # noqa F821

    # TODO: update to look like docs:
    # https://nsls-ii.github.io/sirepo-bluesky/notebooks/srw.html#SRW-Propagation-as-Ophyd-Objects
    (uid,) = RE(bp.scan([w9], post_propagation.hrange_mod, 0.1, 0.3, num_steps))  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(fill=True)
    print(tbl)

    # Check that the duration for each step in the simulation is positive:
    sim_durations = np.array(tbl["w9_duration"])
    assert (sim_durations > 0.0).all(), "Simulation steps did not properly run."

    sample_image = []
    for i in range(num_steps):
        sample_image.append(np.array(list(hdr.data("w9_image"))[i]))

    # Check the shape of the image data is right and that hrange_mod was properly changed:
    for i, hrange_mod in enumerate(np.linspace(0.1, 0.3, num_steps)):
        assert json.loads(tbl["w9_sirepo_data_json"][i + 1])["models"]["postPropagation"][5] == hrange_mod
