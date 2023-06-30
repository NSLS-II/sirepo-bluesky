import json
import pprint

import bluesky.plan_stubs as bps
import dictdiffer
import numpy as np

from sirepo_bluesky.sirepo_bluesky import SirepoBluesky
from sirepo_bluesky.sirepo_ophyd import create_classes
from sirepo_bluesky.utils.json_yaml_converter import dict_to_file


def test_stateless_compute_basic(srw_chx_simulation, RE):
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
    assert diff
    print(diff)

    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)

    crl1 = objects["crl1"]

    print(crl1.summary())  # noqa
    pprint.pprint(crl1.read())  # noqa

    RE(bps.mv(crl1.tipRadius, 150))

    actual_response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)

    assert actual_response.pop("state") == "completed"

    pprint.pprint(actual_response)
    newresponse1 = _remove_dict_strings(actual_response)
    newresponse2 = _remove_dict_strings(expected_response)
    pprint.pprint(newresponse1)
    assert newresponse1.any()

    assert np.allclose(newresponse1, newresponse2)


def test_stateless_compute_advanced(srw_chx_simulation, tmp_path):
    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)

    fname = tmp_path / "test.json"

    _generate_test_file(fname)

    with open(fname, "r") as fp:
        combined_dict = json.load(fp)
    assert combined_dict

    for key in combined_dict["request"]:
        actual_response = srw_chx_simulation.compute_crl_characteristics(combined_dict["request"][key])
        expected_response = combined_dict["response"][key]
        assert actual_response.pop("state") == "completed"
        assert np.allclose(_remove_dict_strings(actual_response), _remove_dict_strings(expected_response))
        print(f"{key} passed")


def _remove_dict_strings(dict):
    newarr = np.array([], dtype=np.float64)
    for key in dict:
        try:
            newarr = np.append(newarr, np.float64(dict[key]))
        except ValueError:
            pass
    return newarr


def _generate_test_file(fname):
    srw_chx_simulation = SirepoBluesky("http://localhost:8000")
    data, _ = srw_chx_simulation.auth("srw", "HXV1JQ5c")
    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)
    crl1 = objects["crl1"]

    combined_dict = {"request": {}, "response": {}}

    for radius in range(1, 201):
        crl1.id._sirepo_dict["tipRadius"] = radius
        expected_response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        combined_dict["request"][f"radius{radius}"] = crl1.id._sirepo_dict.copy()
        combined_dict["response"][f"radius{radius}"] = expected_response
        print(f"Radius {radius} added")
    crl1.id._sirepo_dict["tipRadius"] = 1500

    for lenses in range(1, 201):
        crl1.id._sirepo_dict["numberOfLenses"] = lenses
        expected_response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        combined_dict["request"][f"lenses{lenses}"] = crl1.id._sirepo_dict.copy()
        combined_dict["response"][f"lenses{lenses}"] = expected_response
        print(f"Lenses {lenses} added")
    crl1.id._sirepo_dict["numberOfLenses"] = 1

    for thickness in range(1, 201):
        crl1.id._sirepo_dict["wallThickness"] = thickness
        expected_response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        combined_dict["request"][f"thickness{thickness}"] = crl1.id._sirepo_dict.copy()
        combined_dict["response"][f"thickness{thickness}"] = expected_response
        print(f"Thickness {thickness} added")
    crl1.id._sirepo_dict["wallThickness"] = 80

    dict_to_file(combined_dict, fname)
