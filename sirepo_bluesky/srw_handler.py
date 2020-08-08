import numpy as np
import srwpy.uti_plot_com as srw_io


def read_srw_file(filename, ndim=2):
    data, mode, ranges, labels, units = srw_io.file_load(filename)
    data = np.array(data)
    if ndim == 2:
        data = data.reshape((ranges[8], ranges[5]), order='C')
        photon_energy = ranges[0]
    elif ndim == 1:
        photon_energy = np.linspace(*ranges[:3])
    else:
        raise ValueError(f'The value ndim={ndim} is not supported.')

    return {'data': data,
            'shape': data.shape,
            'mean': np.mean(data),
            'photon_energy': photon_energy,
            'horizontal_extent': ranges[3:5],
            'vertical_extent': ranges[6:8],
            # 'mode': mode,
            'labels': labels,
            'units': units}


class SRWFileHandler:
    specs = {'srw'}

    def __init__(self, filename, ndim=2):
        self._name = filename
        self._ndim = ndim

    def __call__(self):
        d = read_srw_file(self._name, ndim=self._ndim)
        return d['data']
