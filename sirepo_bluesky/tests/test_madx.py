import os
import pprint

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import numpy as np
import pytest
import tfs

from sirepo_bluesky.common.create_classes import create_classes
from sirepo_bluesky.madx.madx_flyer import MADXFlyer


@pytest.mark.madx
@pytest.mark.parametrize("method", ["set", "put"])
def test_mad_x_elements_set_put(madx_resr_storage_ring_simulation, method):
    connection = madx_resr_storage_ring_simulation
    data = connection.data
    classes, objects = create_classes(connection=connection)
    globals().update(**objects)

    for i, (k, v) in enumerate(objects.items()):
        old_value = v.l.get()  # l is length
        old_sirepo_value = data["models"]["elements"][i]["l"]

        getattr(v.l, method)(old_value + 10)

        new_value = v.l.get()
        new_sirepo_value = data["models"]["elements"][i]["l"]

        print(f"\n  Changed: {old_value} -> {new_value}\n   Sirepo: {old_sirepo_value} -> {new_sirepo_value}\n")

        assert old_value == old_sirepo_value
        assert new_value == new_sirepo_value
        assert new_value != old_value
        assert abs(new_value - (old_value + 10)) < 1e-8


@pytest.mark.madx
def test_mad_x_elements_simple_connection(madx_bl2_triplet_tdc_simulation):
    connection = madx_bl2_triplet_tdc_simulation
    classes, objects = create_classes(connection=connection)
    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(bpm5.summary())  # noqa
    pprint.pprint(bpm5.read())  # noqa


@pytest.mark.madx
def test_madx_with_run_engine(RE, db, madx_bl2_triplet_tdc_simulation):
    connection = madx_bl2_triplet_tdc_simulation
    classes, objects = create_classes(connection=connection)
    globals().update(**objects)

    madx_flyer = MADXFlyer(
        connection=connection,
        root_dir="/tmp/sirepo-bluesky-data",
        report="elementAnimation250-20",
    )

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
            assert np.allclose(
                np.array(tbl[f"madx_flyer_{column}"]).astype(float),
                np.array(df[column]),
            )


@pytest.mark.madx
def test_madx_variables_with_run_engine(RE, db, madx_bl2_triplet_tdc_simulation):
    connection = madx_bl2_triplet_tdc_simulation
    data = connection.data
    classes, objects = create_classes(
        connection=connection,
        extra_model_fields=["rpnVariables"],
    )

    globals().update(**objects)

    assert len(objects) == len(data["models"]["elements"]) + len(data["models"]["rpnVariables"])

    madx_flyer = MADXFlyer(
        connection=connection,
        root_dir="/tmp/sirepo-bluesky-data",
        report="elementAnimation250-20",
    )

    def madx_plan(parameter=ihq1, value=2.0):  # noqa F821
        yield from bps.mv(parameter.value, value)
        return (yield from bp.fly([madx_flyer]))

    (uid,) = RE(madx_plan())  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(stream_name="madx_flyer", fill=True)
    print(tbl)

    expected_data_len = 151

    assert len(tbl["madx_flyer_S"]) == expected_data_len
    assert len(tbl["madx_flyer_BETX"]) == expected_data_len
    assert len(tbl["madx_flyer_BETY"]) == expected_data_len


@pytest.mark.madx
def test_madx_commands_with_run_engine(RE, db, madx_bl2_triplet_tdc_simulation):
    connection = madx_bl2_triplet_tdc_simulation
    data = connection.data
    classes, objects = create_classes(
        connection=connection,
        extra_model_fields=["commands"],
    )

    globals().update(**objects)
    pprint.pprint(classes, sort_dicts=False)

    assert len(objects) == len(data["models"]["elements"]) + len(data["models"]["commands"])

    madx_flyer = MADXFlyer(
        connection=connection,
        root_dir="/tmp/sirepo-bluesky-data",
        report="elementAnimation250-20",
    )

    def madx_plan(element=match8, value=1.0):  # noqa F821
        yield from bps.mv(element.deltap, value)
        return (yield from bp.fly([madx_flyer]))

    (uid,) = RE(madx_plan())  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(stream_name="madx_flyer", fill=True)
    print(tbl)

    expected_data_len = 151

    assert len(tbl["madx_flyer_S"]) == expected_data_len
    assert len(tbl["madx_flyer_BETX"]) == expected_data_len
    assert len(tbl["madx_flyer_BETY"]) == expected_data_len


@pytest.mark.madx
def test_madx_variables_and_commands_with_run_engine(RE, db, madx_bl2_triplet_tdc_simulation):
    connection = madx_bl2_triplet_tdc_simulation
    data = connection.data
    classes, objects = create_classes(
        connection=connection,
        extra_model_fields=["rpnVariables", "commands"],
    )

    globals().update(**objects)

    assert len(objects) == len(data["models"]["elements"]) + len(data["models"]["rpnVariables"]) + len(
        data["models"]["commands"]
    )

    madx_flyer = MADXFlyer(
        connection=connection,
        root_dir="/tmp/sirepo-bluesky-data",
        report="elementAnimation250-20",
    )

    def madx_plan(element=match8, parameter=ihq1, value=1.0):  # noqa F821
        yield from bps.mv(element.deltap, value)
        yield from bps.mv(parameter.value, value)
        return (yield from bp.fly([madx_flyer]))

    (uid,) = RE(madx_plan())  # noqa F821
    hdr = db[uid]
    tbl = hdr.table(stream_name="madx_flyer", fill=True)
    print(tbl)

    expected_data_len = 151

    assert len(tbl["madx_flyer_S"]) == expected_data_len
    assert len(tbl["madx_flyer_BETX"]) == expected_data_len
    assert len(tbl["madx_flyer_BETY"]) == expected_data_len
