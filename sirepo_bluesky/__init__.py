import intake
from ophyd import Signal

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

# Look up a driver class by its name in registry.
catalog_class = intake.registry["bluesky-mongo-normalized-catalog"]

sirepo_bluesky_catalog_instance = catalog_class(
    metadatastore_db="mongodb://localhost:27017/md",
    asset_registry_db="mongodb://localhost:27017/ar",
)


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
