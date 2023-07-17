import json
import os
import pprint

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import databroker
import dictdiffer
import numpy as np
import vcr
from databroker import Broker

import sirepo_bluesky.tests
from sirepo_bluesky.sirepo_ophyd import create_classes
from sirepo_bluesky.srw_handler import SRWFileHandler
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
        "attenuationLength": 0.007313,
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
    print(diff)

    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)

    crl1 = objects["crl1"]

    print(crl1.summary())
    pprint.pprint(crl1.read())

    RE(bps.mv(crl1.tipRadius, 150))

    actual_response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)

    assert actual_response.pop("state") == "completed"

    pprint.pprint(actual_response)
    newresponse1 = _remove_dict_strings(actual_response)
    newresponse2 = _remove_dict_strings(expected_response)
    pprint.pprint(newresponse1)
    assert newresponse1.any(), "No response was returned."

    assert np.allclose(newresponse1, newresponse2), "Actual response doesn't match expected response."


@vcr.use_cassette(f"{cassette_location}/test_crl_characteristics.yml")
def test_stateless_compute_crl_characteristics_advanced(srw_chx_simulation, tmp_path):
    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)

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
def test_stateless_compute_crystal(srw_tes_simulation, tmp_path):
    classes, objects = create_classes(srw_tes_simulation.data, connection=srw_tes_simulation)

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


def test_stateless_compute_with_RE(RE, srw_chx_simulation):
    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)
    globals().update(**objects)
    db = Broker.named("local")  # mongodb backend
    try:
        databroker.assets.utils.install_sentinels(db.reg.config, version=1)
    except Exception:
        pass

    RE.subscribe(db.insert)
    db.reg.register_handler("srw", SRWFileHandler, overwrite=True)
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
        print(diff)
        assert diff, "tipRadius not properly updated in RE."


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

    for radius in range(1, 201):
        crl.id._sirepo_dict["tipRadius"] = radius
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        combined_dict["request"][f"radius{radius}"] = crl.id._sirepo_dict.copy()
        combined_dict["response"][f"radius{radius}"] = expected_response
        print(f"Radius {radius} added")
    crl.id._sirepo_dict["tipRadius"] = 1500

    for lenses in range(1, 201):
        crl.id._sirepo_dict["numberOfLenses"] = lenses
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        combined_dict["request"][f"lenses{lenses}"] = crl.id._sirepo_dict.copy()
        combined_dict["response"][f"lenses{lenses}"] = expected_response
        print(f"Lenses {lenses} added")
    crl.id._sirepo_dict["numberOfLenses"] = 1

    for thickness in range(1, 201):
        crl.id._sirepo_dict["wallThickness"] = thickness
        expected_response = simulation.compute_crl_characteristics(crl.id._sirepo_dict)
        combined_dict["request"][f"thickness{thickness}"] = crl.id._sirepo_dict.copy()
        combined_dict["response"][f"thickness{thickness}"] = expected_response
        print(f"Thickness {thickness} added")
    crl.id._sirepo_dict["wallThickness"] = 80

    dict_to_file(combined_dict, fname)


def _generate_test_crystal_file(fname, crystal, simulation):
    combined_dict = {"request": {}, "init": {}, "orientation": {}}

    for energy in range(1, 101):
        crystal.id._sirepo_dict["energy"] = energy
        combined_dict["request"][f"Si energy{energy}"] = crystal.id._sirepo_dict.copy()
        combined_dict["init"][f"Si energy{energy}"] = simulation.compute_crystal_init(crystal.id._sirepo_dict)
        combined_dict["orientation"][f"Si energy{energy}"] = simulation.compute_crystal_orientation(
            crystal.id._sirepo_dict
        )
        print(f"Si Energy {energy} added")
    crystal.id._sirepo_dict["material"] = "Germanium (X0h)"
    for energy in range(1, 21):
        crystal.id._sirepo_dict["energy"] = energy
        combined_dict["request"][f"Ge energy{energy}"] = crystal.id._sirepo_dict.copy()
        combined_dict["init"][f"Ge energy{energy}"] = simulation.compute_crystal_init(crystal.id._sirepo_dict)
        combined_dict["orientation"][f"Ge energy{energy}"] = simulation.compute_crystal_orientation(
            crystal.id._sirepo_dict
        )
        print(f"Ge Energy {energy} added")

    dict_to_file(combined_dict, fname)
