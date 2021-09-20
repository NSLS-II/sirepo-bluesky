import pprint

import pytest

from sirepo_bluesky.sirepo_ophyd import create_classes


def test_beamline_elements_as_ophyd_objects(tes_simulation):
    classes, objects = create_classes(tes_simulation.data,
                                      connection=tes_simulation.sb)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(mono_crystal1.summary())  # noqa
    pprint.pprint(mono_crystal1.read())  # noqa


@pytest.mark.parametrize("method", ["set", "put"])
def test_beamline_elements_set_put(tes_simulation, method):
    classes, objects = create_classes(tes_simulation.data,
                                      connection=tes_simulation.sb)
    globals().update(**objects)

    for i, (k, v) in enumerate(objects.items()):
        old_value = v.element_position.get()
        old_sirepo_value = tes_simulation.data["models"]["beamline"][i]["position"]

        getattr(v.element_position, method)(old_value + 100)

        new_value = v.element_position.get()
        new_sirepo_value = tes_simulation.data["models"]["beamline"][i]["position"]

        print(
            f"\n  Changed: {old_value} -> {new_value}\n   Sirepo: {old_sirepo_value} -> {new_sirepo_value}\n"
        )

        assert old_value == old_sirepo_value
        assert new_value == new_sirepo_value
        assert new_value != old_value
        assert abs(new_value - (old_value + 100)) < 1e-8
