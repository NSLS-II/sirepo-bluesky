from sirepo_bluesky.common.create_classes import create_classes
from sirepo_bluesky.common.sirepo_client import SirepoClient


def populate_beamline(sim_name, *args):
    """
    Parameters
    ----------
    *args :
        For one beamline, ``connection, indices, new_positions``.
        In general:

        .. code-block:: python

            connection1, indices1, new_positions1
            connection2, indices2, new_positions2
            ...,
            connectionN, indicesN, new_positionsN
    """
    if len(args) % 3 != 0:
        raise ValueError(
            "Incorrect signature, arguments must be of the signature: connection, indices, new_positions, ..."
        )

    connections = []
    indices_list = []
    new_positions_list = []

    for i in range(0, len(args), 3):
        connections.append(args[i])
        indices_list.append(args[i + 1])
        new_positions_list.append(args[i + 2])

    emptysim = SirepoClient("http://localhost:8000")
    emptysim.auth("srw", sim_id="emptysim")
    new_beam = emptysim.copy_sim(sim_name=sim_name)
    new_beamline = new_beam.data["models"]["beamline"]
    new_propagation = new_beam.data["models"]["propagation"]

    curr_id = 0
    for connection, indices, new_positions in zip(connections, indices_list, new_positions_list):
        old_beamline = connection.data["models"]["beamline"]
        old_propagation = connection.data["models"]["propagation"]
        for i, pos in zip(indices, new_positions):
            new_beamline.append(old_beamline[i].copy())
            new_beamline[curr_id]["id"] = curr_id
            new_beamline[curr_id]["position"] = pos
            new_propagation[str(curr_id)] = old_propagation[str(old_beamline[i]["id"])].copy()
            curr_id += 1

    classes, objects = create_classes(new_beam)

    return new_beam, classes, objects
