import tfs
from area_detector_handlers import HandlerBase


def read_madx_file(filename):
    df = tfs.read(filename)
    return df


class MADXFileHandler(HandlerBase):
    def __init__(self, filename):
        self._filename = filename
        self._dataframe = read_madx_file(self._filename)

    def __call__(self, row_num=0, col_name="NAME"):
        return self._dataframe[col_name][row_num]
