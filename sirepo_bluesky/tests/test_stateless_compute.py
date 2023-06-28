import pprint

import bluesky.plan_stubs as bps
import dictdiffer
import numpy as np

from sirepo_bluesky.sirepo_ophyd import create_classes


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


def test_stateless_compute_advanced(srw_chx_simulation, RE):
    classes, objects = create_classes(srw_chx_simulation.data, connection=srw_chx_simulation)

    crl1 = objects["crl1"]

    for i in range(1, 1001):
        RE(bps.mv(crl1.tipRadius, i))

        response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        crl1.id._sirepo_dict = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        assert response.pop("state") == "completed"

        list1 = _remove_dict_strings(response)
        list2 = _remove_dict_strings(crl1.id._sirepo_dict)

        assert np.allclose(list1, list2)

        print(f"Test Radius {i} Passed")

    for i in range(1, 11):
        RE(bps.mv(crl1.numberOfLenses, i))

        response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        crl1.id._sirepo_dict = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        assert response.pop("state") == "completed"

        list1 = _remove_dict_strings(response)
        list2 = _remove_dict_strings(crl1.id._sirepo_dict)

        assert np.allclose(list1, list2)

        print(f"Test Lenses {i} Passed")

    for i in range(1, 101):
        RE(bps.mv(crl1.wallThickness, i))

        response = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        crl1.id._sirepo_dict = srw_chx_simulation.compute_crl_characteristics(crl1.id._sirepo_dict)
        assert response.pop("state") == "completed"

        list1 = _remove_dict_strings(response)
        list2 = _remove_dict_strings(crl1.id._sirepo_dict)

        assert np.allclose(list1, list2)

        print(f"Test Wall Thickness {i} Passed")


def _remove_dict_strings(dict):
    newarr = np.array([], dtype=np.float64)
    for key in dict:
        try:
            newarr = np.append(newarr, np.float64(dict[key]))
        except ValueError:
            pass
    return newarr
