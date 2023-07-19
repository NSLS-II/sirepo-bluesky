import json
import os
import pprint

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import dictdiffer
import numpy as np
import vcr

import sirepo_bluesky.tests
from sirepo_bluesky.sirepo_ophyd import create_classes
from sirepo_bluesky.utils.json_yaml_converter import dict_to_file

cassette_location = os.path.join(os.path.dirname(sirepo_bluesky.tests.__file__), "vcr_cassettes")


def test_stateless_compute_crl_characteristics_basic(srw_chx_simulation, RE):
    # changed tipRadius from 1500 to 150
    browser_request = {
        "absoluteFocusPosition": -8.7725,
        "attenuationLength": 0.007313,
        "focalDistance": 178.2502,
        "focalPlane": "2",
        "horizontalApertureSize": "1",
        "horizontalOffset": 0,
        "id": 6,
        "material": "User-defined",
        "method": "server",
        "numberOfLenses": "1",
        "position": "35.4",
        "radius": "1.5e-03",
        "refractiveIndex": "4.207568e-6",
        "shape": "1",
        "tipRadius": 150,
        "tipWallThickness": 80,
        "title": "CRL1",
        "type": "crl",
        "verticalApertureSize": "2.4",
        "verticalOffset": 0,
        "wallThickness": "80.e-06",
    }
    expected_response = {
        "absoluteFocusPosition": 71.3036529974982,
        "attenuationLength": "0.007313",
        "focalDistance": 17.825023861765274,
        "focalPlane": "2",
        "horizontalApertureSize": "1",
        "horizontalOffset": 0,
        "id": 6,
        "material": "User-defined",
        "method": "server",
        "numberOfLenses": "1",
        "position": "35.4",
        "radius": "1.5e-03",
        "refractiveIndex": "4.207568e-6",
        "shape": "1",
        "tipRadius": 150,
        "tipWallThickness": 80,
        "title": "CRL1",
        "type": "crl",
        "verticalApertureSize": "2.4",
        "verticalOffset": 0,
        "wallThickness": "80.e-06",
    }

    diff = list(dictdiffer.diff(browser_request, expected_response))
    assert diff, "The browser request and expected response match, but are expected to be different."
    pprint.pprint(diff)

    classes, objects = create_classes(connection=srw_chx_simulation)

    crl1 = objects["crl1"]

    print(crl1.summary())
    pprint.pprint(crl1.read())

    RE(bps.mv(crl1.tipRadius, 150))

    actual_response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)

    assert actual_response.pop("state") == "completed"
    diff2 = list(dictdiffer.diff(actual_response, expected_response))
    pprint.pprint(diff2)
    assert not diff2, "Actual response doesn't match expected response."


def test_stateless_compute_crystal_orientation_basic(srw_tes_simulation, RE):
    classes, objects = create_classes(connection=srw_tes_simulation)
    globals().update(**objects)
    mc1 = mono_crystal1  # noqa

    # changed energy from 2500 to 2000
    browser_request = {
        "asymmetryAngle": 0,
        "crystalThickness": 0.003,
        "dSpacing": 3.1355713563754857,
        "diffractionAngle": "0",
        "energy": 2000,
        "grazingAngle": 912.3126255115334,
        "h": "1",
        "heightAmplification": 1,
        "heightProfileFile": "",
        "id": 4,
        "k": "1",
        "l": "1",
        "material": "Si (SRW)",
        "nvx": 0,
        "nvy": 0.6119182833983884,
        "nvz": -0.7909209912771121,
        "orientation": "y",
        "outframevx": 1,
        "outframevy": 0,
        "outoptvx": 0,
        "outoptvy": 0.9679580305720843,
        "outoptvz": -0.25111202888553913,
        "position": 25,
        "psi0i": 0.000028733167819721347,
        "psi0r": -0.00015133473800612508,
        "psiHBi": 0.00002006074060738366,
        "psiHBr": -0.00007912710547916795,
        "psiHi": 0.00002006074060738366,
        "psiHr": -0.00007912710547916795,
        "rotationAngle": 0,
        "title": "Mono Crystal 1",
        "transmissionImage": "1",
        "tvx": 0,
        "tvy": 0.7909209912771121,
        "type": "crystal",
        "useCase": "1",
    }
    expected_response = {
        "asymmetryAngle": 0,
        "crystalThickness": 0.003,
        "dSpacing": 3.1355713563754857,
        "diffractionAngle": "0",
        "energy": 2000,
        "grazingAngle": 1419.9107955732711,
        "h": "1",
        "heightAmplification": 1,
        "heightProfileFile": "",
        "id": 4,
        "k": "1",
        "l": "1",
        "material": "Si (SRW)",
        "nvx": 0,
        "nvy": 0.15031366142760424,
        "nvz": -0.9886383581412506,
        "orientation": "y",
        "outframevx": 1.0,
        "outframevy": 0.0,
        "outoptvx": 0.0,
        "outoptvy": 0.29721170287997256,
        "outoptvz": -0.9548116063764552,
        "position": 25,
        "psi0i": 6.530421915581681e-05,
        "psi0r": -0.00020558072555357544,
        "psiHBi": 4.559368494529194e-05,
        "psiHBr": -0.00010207663788071082,
        "psiHi": 4.559368494529194e-05,
        "psiHr": -0.00010207663788071082,
        "rotationAngle": 0,
        "title": "Mono Crystal 1",
        "transmissionImage": "1",
        "tvx": 0,
        "tvy": 0.9886383581412506,
        "type": "crystal",
        "useCase": "1",
    }

    diff = list(dictdiffer.diff(browser_request, expected_response))
    assert diff, "The browser request and expected response match, but are expected to be different."
    pprint.pprint(diff)

    RE(bps.mv(mc1.energy, 2000))

    actual_response = srw_tes_simulation.compute_crystal_orientation(mc1.id._sirepo_dict)

    assert actual_response.pop("state") == "completed"
    diff2 = list(dictdiffer.diff(actual_response, expected_response))
    pprint.pprint(diff2)
    assert not diff2, "Actual response doesn't match expected response."


@vcr.use_cassette(f"{cassette_location}/test_crl_characteristics.yml")
def test_stateless_compute_crl_characteristics_advanced(srw_chx_simulation, tmp_path):
    classes, objects = create_classes(connection=srw_chx_simulation)

    _generate_test_crl_file(tmp_path / "test_crl_characteristics.json", objects["crl1"], srw_chx_simulation)

    with open(tmp_path / "test_crl_characteristics.json", "r") as fp:
        combined_dict = json.load(fp)
    assert combined_dict

    for key in combined_dict["request"]:
        actual_response = srw_chx_simulation.compute_crl_characteristics(combined_dict["request"][key])
        expected_response = combined_dict["response"][key]
        actual_response.pop("state")
        assert np.allclose(_remove_dict_strings(actual_response), _remove_dict_strings(expected_response))
        print(f"{key} passed")


@vcr.use_cassette(f"{cassette_location}/test_crystal_characteristics.yml")
def test_stateless_compute_crystal_advanced(srw_tes_simulation, tmp_path):
    classes, objects = create_classes(connection=srw_tes_simulation)

    _generate_test_crystal_file(
        tmp_path / "test_compute_crystal.json", objects["mono_crystal1"], srw_tes_simulation
    )

    with open(tmp_path / "test_compute_crystal.json", "r") as fp:
        combined_dict = json.load(fp)
    assert combined_dict

    for key in combined_dict["request"]:
        actual_init = srw_tes_simulation.compute_crystal_init(combined_dict["request"][key])
        expected_init = combined_dict["init"][key]
        actual_init.pop("state")
        assert np.allclose(_remove_dict_strings(actual_init), _remove_dict_strings(expected_init))

        actual_orientation = srw_tes_simulation.compute_crystal_orientation(combined_dict["request"][key])
        expected_orientation = combined_dict["orientation"][key]
        actual_orientation.pop("state")
        assert np.allclose(_remove_dict_strings(actual_orientation), _remove_dict_strings(expected_orientation))
        print(f"{key} passed")


def test_stateless_compute_with_RE(RE, srw_chx_simulation, db):
    classes, objects = create_classes(connection=srw_chx_simulation)
    globals().update(**objects)
    crl1.tipRadius.kind = "hinted"  # noqa
    sample.duration.kind = "hinted"  # noqa

    (uid,) = RE(bp.scan([sample], crl1.tipRadius, 500, 2500, 5))  # noqa

    hdr = db[uid]
    tbl = hdr.table(fill=True)

    sirepo_dicts = []
    for data in tbl["sample_sirepo_data_json"]:
        sirepo_dicts.append(json.loads(data))
    for i in range(0, len(sirepo_dicts) - 1):
        diff = list(dictdiffer.diff(sirepo_dicts[i], sirepo_dicts[i + 1]))
        pprint.pprint(diff)
        assert diff, "tipRadius not properly updated in RE."
    for data, tbl_radius, radius in zip(sirepo_dicts, tbl["crl1_tipRadius"], np.linspace(500, 2500, 5)):
        assert (
            data["models"]["beamline"][4]["tipRadius"] == radius
        ), "Radius was not properly changed in the Run Engine."
        assert tbl_radius == radius, "Radius was not properly changed in the Run Engine."


def _remove_dict_strings(dict):
    newarr = []
    for key in dict:
        if dict[key] is not None:
            try:
                newarr = np.append(newarr, np.float64(dict[key]))
            except ValueError:
                pass
    return newarr


def _generate_test_crl_file(fname, crl, simulation):
    combined_dict = {"request": {}, "response": {}}

    for material in ["Al", "Au", "B", "Be", "C"]:
        crl.id._sirepo_dict["material"] = material
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        combined_dict["request"][material] = crl.id._sirepo_dict.copy()
        combined_dict["response"][material] = expected_response
        print(f"Material {material} added")
    crl.id._sirepo_dict["material"] = "User-defined"
    for radius in range(1000, 2100, 100):
        crl.id._sirepo_dict["tipRadius"] = radius
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        key = f"Radius {radius} µm"
        combined_dict["request"][key] = crl.id._sirepo_dict.copy()
        combined_dict["response"][key] = expected_response
        print(f"{key} added")
    crl.id._sirepo_dict["tipRadius"] = 1500

    for lenses in range(1, 11):
        crl.id._sirepo_dict["numberOfLenses"] = lenses
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        key = f"Lenses {lenses}"
        combined_dict["request"][key] = crl.id._sirepo_dict.copy()
        combined_dict["response"][key] = expected_response
        print(f"{key} added")
    crl.id._sirepo_dict["numberOfLenses"] = 1

    for thickness in range(20, 205, 5):
        crl.id._sirepo_dict["wallThickness"] = thickness
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        key = f"Thickness {thickness} µm"
        combined_dict["request"][key] = crl.id._sirepo_dict.copy()
        combined_dict["response"][key] = expected_response
        print(f"{key} added")
    crl.id._sirepo_dict["wallThickness"] = 80

    dict_to_file(combined_dict, fname)


def _generate_test_crystal_file(fname, crystal, simulation):
    combined_dict = {"request": {}, "init": {}, "orientation": {}}

    for energy in range(100, 10100, 1000):
        crystal.id._sirepo_dict["energy"] = energy
        key = f"Si {energy} eV"
        combined_dict["request"][key] = crystal.id._sirepo_dict.copy()
        combined_dict["init"][key] = simulation.compute_crystal_init(crystal.id._sirepo_dict)
        combined_dict["orientation"][key] = simulation.compute_crystal_orientation(crystal.id._sirepo_dict)
        print(f"{key} added")
    crystal.id._sirepo_dict["material"] = "Germanium (X0h)"
    for energy in range(1000, 3100, 100):
        crystal.id._sirepo_dict["energy"] = energy
        key = f"Ge {energy} eV"
        combined_dict["request"][key] = crystal.id._sirepo_dict.copy()
        combined_dict["init"][key] = simulation.compute_crystal_init(crystal.id._sirepo_dict)
        combined_dict["orientation"][key] = simulation.compute_crystal_orientation(crystal.id._sirepo_dict)
        print(f"{key} added")

    dict_to_file(combined_dict, fname)
