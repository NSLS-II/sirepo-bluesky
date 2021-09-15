import copy
import pprint
import sirepo_bluesky.srw_detector as sd
from ophyd import Device, Component as Cpt, Signal


def test_beamline_elements_as_ophyd_objects(RE, db, tmpdir):
    srw_det = sd.SirepoSRWDetector(sim_type="srw",
                                   sim_id="00000002",
                                   sirepo_server="http://localhost:8000",
                                   watch_name="W9")
    classes = {}
    objects = {}
    keys_to_remove = {"position"}
    data = copy.deepcopy(srw_det.data)
    for el in data["models"]["beamline"]:
        for key in keys_to_remove:
            el[f"element_{key}"] = el[key]
            el.pop(key)
        el["title"] = el["title"].replace(" ", "")
        title = el["title"]
        cls = type(title, (Device,), {k: Cpt(Signal, value=v) for k, v in el.items()})
        classes[title] = cls
        objects[title] = cls(name=title)
        # ip.user_ns.update(**objects)

    for name, obj in objects.items():
        pprint.pprint(obj.read())

    globals().update(**objects)

    print(Aperture.summary())
    pprint.pprint(Aperture.read())
