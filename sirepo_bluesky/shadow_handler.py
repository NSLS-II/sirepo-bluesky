import contextlib
import os

import numpy as np
import Shadow.ShadowLibExtensions as sd
import Shadow.ShadowTools

from . import utils


def read_shadow_file_col(filename, parameter=30):
    """Read specified parameter from the Shadow3 output binary file.

    Parameters
    ----------
    filename : str
        Shadow3 output binary file (.dat)
    parameter : int
        The parameter to read.

        Available columns (from
        https://github.com/oasys-kit/shadow3/blob/master/Shadow/ShadowTools.py):
           1   X spatial coordinate [user's unit]
           2   Y spatial coordinate [user's unit]
           3   Z spatial coordinate [user's unit]
           4   X' direction or divergence [rads]
           5   Y' direction or divergence [rads]
           6   Z' direction or divergence [rads]
           7   X component of the electromagnetic vector (s-polariz)
           8   Y component of the electromagnetic vector (s-polariz)
           9   Z component of the electromagnetic vector (s-polariz)
          10   Lost ray flag
          11   Energy [eV]
          12   Ray index
          13   Optical path length
          14   Phase (s-polarization)
          15   Phase (p-polarization)
          16   X component of the electromagnetic vector (p-polariz)
          17   Y component of the electromagnetic vector (p-polariz)
          18   Z component of the electromagnetic vector (p-polariz)
          19   Wavelength [A]
          20   R= SQRT(X^2+Y^2+Z^2)
          21   angle from Y axis
          22   the magnituse of the Electromagnetic vector
          23   |E|^2 (total intensity)
          24   total intensity for s-polarization
          25   total intensity for p-polarization
          26   K = 2 pi / lambda [A^-1]
          27   K = 2 pi / lambda * col4 [A^-1]
          28   K = 2 pi / lambda * col5 [A^-1]
          29   K = 2 pi / lambda * col6 [A^-1]
          30   S0-stokes = |Es|^2 + |Ep|^2
          31   S1-stokes = |Es|^2 - |Ep|^2
          32   S2-stokes = 2 |Es| |Ep| cos(phase_s-phase_p)
          33   S3-stokes = 2 |Es| |Ep| sin(phase_s-phase_p)
    """
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull):
            data = Shadow.ShadowTools.getshcol(filename, col=parameter)

    mean_value = np.mean(data)

    return {
        "data": data,
        "shape": data.shape,
        "mean": mean_value,
        "photon_energy": mean_value,
        "horizontal_extent": [0, 1],
        "vertical_extent": [0, 1],
        # 'labels': labels,
        # 'units': units,
    }


def read_shadow_file(filename, histogram_bins=None):
    if histogram_bins is None:
        raise ValueError("'histogram_bins' kwarg should be specified.")

    beam = sd.Beam()
    beam.load(filename)

    # 1=X spatial coordinate; 3=Z spatial coordinate
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull):
            data_dict = beam.histo2(1, 3, nolost=1, nbins=histogram_bins)

            # This returns a list of N values (N=number of rays)
            photon_energy_list = Shadow.ShadowTools.getshcol(filename, col=11)  # 11=Energy [eV]

    data = data_dict["histogram"]
    photon_energy = np.mean(photon_energy_list)

    # convert to um
    horizontal_extent = 1e3 * np.array(data_dict["xrange"][:2])
    vertical_extent = 1e3 * np.array(data_dict["yrange"][:2])

    ret = {
        "data": data,
        "shape": data.shape,
        "flux": data.sum(),
        "mean": data.mean(),
        "photon_energy": photon_energy,
        "horizontal_extent": horizontal_extent,
        "vertical_extent": vertical_extent,
        "units": "um",
    }

    ret.update(utils.get_beam_stats(data, horizontal_extent, vertical_extent))

    return ret


class ShadowFileHandler:
    specs = {"shadow"}

    def __init__(self, filename, histogram_bins, **kwargs):
        self._name = filename
        self._histogram_bins = histogram_bins

    def __call__(self, **kwargs):
        d = read_shadow_file(self._name, histogram_bins=self._histogram_bins)
        return d["data"]
