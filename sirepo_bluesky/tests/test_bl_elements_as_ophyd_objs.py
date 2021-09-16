import pprint

import sirepo_bluesky.srw_detector as sd
from sirepo_bluesky.sirepo_ophyd import create_classes


def test_beamline_elements_as_ophyd_objects(RE, db, tmpdir):
    srw_det = sd.SirepoSRWDetector(
        sim_type="srw",
        sim_id="00000002",
        sirepo_server="http://localhost:8000",
        watch_name="W9",
    )
    classes, objects = create_classes(srw_det.data)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(Aperture.summary())  # noqa
    pprint.pprint(Aperture.read())  # noqa
