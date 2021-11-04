import json
import pprint

import bluesky.plans as bp
import dictdiffer
import pytest

from sirepo_bluesky.sirepo_ophyd import create_classes


def test_beamline_elements_as_ophyd_objects(srw_tes_simulation):
    classes, objects = create_classes(srw_tes_simulation.data,
                                      connection=srw_tes_simulation)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(mono_crystal1.summary())  # noqa
    pprint.pprint(mono_crystal1.read())  # noqa


@pytest.mark.parametrize("method", ["set", "put"])
def test_beamline_elements_set_put(srw_tes_simulation, method):
    classes, objects = create_classes(srw_tes_simulation.data,
                                      connection=srw_tes_simulation)
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


def test_beamline_elements_simple_connection(srw_basic_simulation):
    classes, objects = create_classes(srw_basic_simulation.data,
                                      connection=srw_basic_simulation)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(watchpoint.summary())  # noqa
    pprint.pprint(watchpoint.read())  # noqa


def test_beam_statistics_report(RE, db, shadow_tes_simulation):
    from sirepo_bluesky.sirepo_ophyd import create_classes
    classes, objects = create_classes(shadow_tes_simulation.data,
                                      connection=shadow_tes_simulation)
    globals().update(**objects)
    from sirepo_bluesky.sirepo_ophyd import BeamStatisticsReport
    bsr = BeamStatisticsReport(name="bsr", connection=shadow_tes_simulation)

    toroid.r_maj.kind = 'hinted'  # noqa F821

    uid, = RE(bp.scan([bsr, w9], toroid.r_maj, 10000, 50000, 5))  # noqa F821
    hdr = db[uid]
    print(hdr.table())

    w9_data_1 = json.loads(hdr.table()["w9_sirepo_data_json"][1])
    w9_data_5 = json.loads(hdr.table()["w9_sirepo_data_json"][5])

    bsr_data_1 = json.loads(hdr.table()["bsr_sirepo_data_json"][1])
    bsr_data_5 = json.loads(hdr.table()["bsr_sirepo_data_json"][5])

    w9_diffs = list(dictdiffer.diff(w9_data_1, w9_data_5))
    assert w9_diffs == [('change', ['models', 'beamline', 5, 'r_maj'],
                         (10000.0, 50000.0))]

    bsr_diffs = list(dictdiffer.diff(bsr_data_1, bsr_data_5))
    assert bsr_diffs == [('change', ['models', 'beamline', 5, 'r_maj'],
                          (10000.0, 50000.0))]

    w9_bsr_diffs = list(dictdiffer.diff(w9_data_1, bsr_data_5))
    assert w9_bsr_diffs == [('change', ['models', 'beamline', 5, 'r_maj'],
                             (10000.0, 50000.0)),
                            ('change', 'report',
                             ('watchpointReport13', 'beamStatisticsReport'))]
