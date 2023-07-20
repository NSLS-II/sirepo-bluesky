import numpy as np
import srwpy.uti_plot_com as srw_io

from . import utils


def read_srw_file(filename, ndim=2):
    data, mode, ranges, labels, units = srw_io.file_load(filename)
    data = np.array(data)
    if ndim == 2:
        data = data.reshape((ranges[8], ranges[5]), order="C")
        photon_energy = ranges[0]
    elif ndim == 1:
        photon_energy = np.linspace(*ranges[:3])
    else:
        raise ValueError(f"The value ndim={ndim} is not supported.")

    horizontal_extent = np.array(ranges[3:5])
    vertical_extent = np.array(ranges[6:8])

    ret = {
        "data": data,
        "shape": data.shape,
        "flux": data.sum(),
        "mean": data.mean(),
        "photon_energy": photon_energy,
        "horizontal_extent": horizontal_extent,
        "vertical_extent": vertical_extent,
        "labels": labels,
        "units": units,
    }

    if ndim == 1:
        ret.update({key: np.nan for key in ["x", "y", "fwhm_x", "fwhm_y"]})
    if ndim == 2:
        ret.update(utils.get_beam_stats(data, horizontal_extent, vertical_extent))

    return ret


class SRWFileHandler:
    specs = {"srw"}

    def __init__(self, filename, ndim=2):
        self._name = filename
        self._ndim = ndim

    def __call__(self):
        d = read_srw_file(self._name, ndim=self._ndim)
        return d["data"]
