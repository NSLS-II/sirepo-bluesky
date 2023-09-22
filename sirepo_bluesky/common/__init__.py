import logging
from collections import deque

from ophyd import Signal
from ophyd.sim import NullStatus

logger = logging.getLogger("sirepo-bluesky")
# Note: the following handler could be created/added to the logger on the client side:
# import sys
# stream_handler = logging.StreamHandler(sys.stdout)
# logger.addHandler(stream_handler)

RESERVED_OPHYD_TO_SIREPO_ATTRS = {  # ophyd <-> sirepo
    "position": "element_position",
    "name": "element_name",
    "class": "command_class",
}
RESERVED_SIREPO_TO_OPHYD_ATTRS = {v: k for k, v in RESERVED_OPHYD_TO_SIREPO_ATTRS.items()}


class ExternalFileReference(Signal):
    """
    A pure software Signal that describe()s an image in an external file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def describe(self):
        resource_document_data = super().describe()
        resource_document_data[self.name].update(
            dict(
                external="FILESTORE:",
                dtype="array",
            )
        )
        return resource_document_data


class SirepoSignal(Signal):
    def __init__(self, sirepo_dict, sirepo_param, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sirepo_dict = sirepo_dict
        self._sirepo_param = sirepo_param
        if sirepo_param in RESERVED_SIREPO_TO_OPHYD_ATTRS:
            self._sirepo_param = RESERVED_SIREPO_TO_OPHYD_ATTRS[sirepo_param]

    def set(self, value, *, timeout=None, settle_time=None):
        logger.debug(f"Setting value for {self.name} to {value}")
        self._sirepo_dict[self._sirepo_param] = value
        self._readback = value
        return NullStatus()

    def put(self, *args, **kwargs):
        self.set(*args, **kwargs).wait()


class ReadOnlyException(Exception):
    ...


class SirepoSignalRO(SirepoSignal):
    def set(self, *args, **kwargs):
        raise ReadOnlyException("Cannot set/put the read-only signal.")


class BlueskyFlyer:
    def __init__(self):
        self.name = "bluesky_flyer"
        self._asset_docs_cache = deque()
        self._resource_uids = []
        self._datum_counter = None
        self._datum_ids = []

    def kickoff(self):
        return NullStatus()

    def complete(self):
        return NullStatus()

    def collect(self):
        ...

    def collect_asset_docs(self):
        items = list(self._asset_docs_cache)
        self._asset_docs_cache.clear()
        for item in items:
            yield item
