from ._version import get_versions
from .utils import prepare_re_env  # noqa: F401

__version__ = get_versions()["version"]
del get_versions
