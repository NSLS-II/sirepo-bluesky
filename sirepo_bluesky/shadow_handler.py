import numpy as np
import Shadow.ShadowTools


def read_shadow_file(filename, parameter=11):
    """Read specified parameter from the Shadow3 output binary file.

    Parameters
    ----------
    filename : str
        Shadow3 output binary file (.dat)
    parameter : int
        The parameter to read (11=Energy [eV] by default)
    """
    data = Shadow.ShadowTools.getshcol(filename, col=parameter)

    mean_value = np.mean(data)

    return {'data': data,
            'shape': data.shape,
            'mean': mean_value,
            'photon_energy': mean_value,
            'horizontal_extent': 1000,
            'vertical_extent': 1000,
            # 'labels': labels,
            # 'units': units,
            }


class ShadowFileHandler:
    specs = {'shadow'}

    def __init__(self, filename):
        self._name = filename

    def __call__(self):
        d = read_shadow_file(self._name)
        return d['data']
