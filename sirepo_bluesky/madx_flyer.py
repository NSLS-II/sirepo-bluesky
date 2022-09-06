from collections import deque
import datetime
from event_model import compose_resource
from ophyd.sim import NullStatus, new_uid
from pathlib import Path
import time as ttime

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
        self._datum_docs = deque()

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

        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec=self.connection.data["simulationType"],
            root=self._root_dir,
            resource_path=str(Path(self._assets_dir) / Path(self._result_file)),
            resource_kwargs={},
        )
        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        sim_result_file = str(
            Path(self._resource_document["root"])
            / Path(self._resource_document["resource_path"])
        )

        with open(sim_result_file, "wb") as file:
            file.write(datafile)

        # Store the dataframe from raw madx datafile
        self._dataframe = read_madx_file(sim_result_file)

        return NullStatus()

    def complete(self, *args, **kwargs):
        # 2 for loops, name of column and row num
        for row_num in [0]:
            for col_name in ["NAME", "S"]:
                datum_document = self._datum_factory(datum_kwargs={"row_num": row_num, "col_name": col_name})
                print(f"{datum_document = }")
                self._datum_docs.append(datum_document)
                self._asset_docs_cache.append(("datum", datum_document))
        return NullStatus()

    def describe_collect(self):
        # parameterize - stash list of columns
        return_dict = {self.name:
                       {f'{self.name}_NAME': {'source': f'{self.name}_NAME',
                                               'dtype': 'string',
                                               'shape': [],
                                               'external': 'MADXFILE:'},
                        f'{self.name}_S': {'source': f'{self.name}_S',
                                               'dtype': 'number',
                                               'shape': [],
                                               'external': 'MADXFILE:'},
                        }
                       }
        return return_dict

    def collect(self):
        now = ttime.time()
        data_dict = {}
        for i, datum_doc in enumerate(self._datum_docs):
            data_dict[f'{self.name}_{datum_doc["datum_kwargs"]["col_name"]}'] = datum_doc["datum_id"]
        yield {'data': data_dict,
               'timestamps': {key: now for key in data_dict},
               'time': now,
               'filled': {key: False for key in data_dict}}
