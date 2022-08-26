import datetime
from ophyd.sim import NullStatus, new_uid
from pathlib import Path

from .madx_handler import read_madx_file
from .sirepo_flyer import BlueskyFlyer


class MADXFlyer(BlueskyFlyer):
    # TODO: Need SirepoFlyer which subclasses from BlueskyFlyer
    # and then all other Sirepo applications subclass from SirepoFlyer
    def __init__(self, connection, root_dir, report):
        super().__init__()
        self.name = 'madx_flyer'
        self.connection = connection
        self._root_dir = root_dir
        self.report = report  # TODO: property

    def __repr__(self):
        return (f'Flyer with sim_type={self.connection.sim_type} and '
                f'sim_id="{self.connection.sim_id}" at {self.connection.server}')

    def kickoff(self):
        self.connection.data['report'] = self.report
        self.connection.data['forceRun'] = True
        res, elapsed_time = self.connection.run_simulation()
        datafile = self.connection.get_datafile(file_index=0)

        date = datetime.datetime.now()
        self._assets_dir = date.strftime("%Y/%m/%d")
        self._result_file = f"{new_uid()}.tfs"

        sim_result_file = str(
            Path(self._root_dir)
            / Path(self._assets_dir)
            / Path(self._result_file)
        )

        with open(sim_result_file, "wb") as file:
            file.write(datafile)

        read_madx_file(datafile)


        return NullStatus()

    def complete(self, *args, **kwargs):
        datum_id = self._resource_uids[i]
        datum = {'resource': self._resource_uids[i],
                    'datum_kwargs': {},
                    'datum_id': datum_id}
        self._asset_docs_cache.append(('datum', datum))
        self._datum_ids.append(datum_id)
        return NullStatus()

    def describe_collect(self):
        ...

    def collect(self):
        ...