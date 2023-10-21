import datetime
import itertools
import os
import time
from collections import OrderedDict, namedtuple
from pathlib import Path

import h5py
import numpy as np
from event_model import compose_resource
from ophyd.sim import NullStatus, new_uid
from skimage.transform import resize

from sirepo_bluesky.common import SirepoSignal, logger
from sirepo_bluesky.common.base_classes import SirepoWatchpointBase
from sirepo_bluesky.srw.srw_handler import read_srw_file


class SirepoWatchpointSRW(SirepoWatchpointBase):
    def __init__(
        self,
        *args,
        root_dir="/tmp/sirepo-bluesky-data",
        assets_dir=None,
        result_file=None,
        image_shape=(1024, 1024),
        **kwargs,
    ):
        self._allowed_sim_types = ("srw",)
        self._image_shape = image_shape
        super().__init__(*args, root_dir=root_dir, assets_dir=assets_dir, result_file=result_file, **kwargs)

    def stage(self):
        super().stage()
        date = datetime.datetime.now()
        self._assets_dir = date.strftime("%Y/%m/%d")
        data_file = f"{new_uid()}.h5"

        self._resource_document, self._datum_factory, _ = compose_resource(
            start={"uid": "needed for compose_resource() but will be discarded"},
            spec=f'{self.connection.data["simulationType"]}_hdf5'.upper(),
            root=self._root_dir,
            resource_path=str(Path(self._assets_dir) / Path(data_file)),
            resource_kwargs={},
        )

        self._data_file = str(
            Path(self._resource_document["root"]) / Path(self._resource_document["resource_path"])
        )

        # now discard the start uid, a real one will be added later
        self._resource_document.pop("run_start")
        self._asset_docs_cache.append(("resource", self._resource_document))

        self._h5file_desc = h5py.File(self._data_file, "x")
        group = self._h5file_desc.create_group("/entry")
        self._dataset = group.create_dataset(
            "image",
            data=np.full(fill_value=np.nan, shape=(1, *self._image_shape)),
            maxshape=(None, *self._image_shape),
            chunks=(1, *self._image_shape),
            dtype="float64",
            compression="lzf",
        )
        self._counter = itertools.count()

    def describe(self):
        res = super().describe()

        res[self.image.name].update(dict(external="FILESTORE", shape=self._image_shape))

        return res

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        self.connection.data["report"] = self._report

        current_frame = next(self._counter)
        sim_result_file = f"{os.path.splitext(self._data_file)[0]}_{self._sim_type}_{current_frame:04d}.dat"

        _, duration = self.connection.run_simulation()
        self.duration.put(duration)

        datafile = self.connection.get_datafile(file_index=-1)

        with open(sim_result_file, "wb") as f:
            f.write(datafile)

        ndim = 2  # this will always be a report with 2D data.
        ret = read_srw_file(sim_result_file, ndim=ndim)
        # TODO: rename _image_shape to _target_image_shape?
        data = resize(ret["data"], self._image_shape)
        self._dataset.resize((current_frame + 1, *self._image_shape))

        logger.debug(f"{self._dataset = }\n{self._dataset.shape = }")

        self._dataset[current_frame, :, :] = data

        def update_components(_data):
            self.flux.put(_data["flux"])
            self.mean.put(_data["mean"])
            self.x.put(_data["x"])
            self.y.put(_data["y"])
            self.fwhm_x.put(_data["fwhm_x"])
            self.fwhm_y.put(_data["fwhm_y"])
            self.photon_energy.put(_data["photon_energy"])
            self.horizontal_extent_start.put(_data["horizontal_extent_start"])
            self.horizontal_extent_end.put(_data["horizontal_extent_end"])
            self.vertical_extent_start.put(_data["vertical_extent_start"])
            self.vertical_extent_end.put(_data["vertical_extent_end"])

        # TODO: think about what should be passed - raw data from .dat files or the resized data?
        update_components(ret)

        datum_document = self._datum_factory(datum_kwargs={"frame": current_frame})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        logger.debug(f"\nReport for {self.name}: {self.connection.data['report']}\n")

        # We call the trigger on super at the end to update the sirepo_data_json
        # and the corresponding hash after the simulation is run.
        super().trigger(*args, **kwargs)
        return NullStatus()

    def unstage(self):
        super().unstage()
        self._resource_document = None
        self._datum_factory = None
        del self._dataset
        self._h5file_desc.close()


# This is for backwards compatibility
SirepoWatchpoint = SirepoWatchpointSRW


class SingleElectronSpectrumReport(SirepoWatchpointSRW):
    horizontal_extent_start = None
    horizontal_extent_end = None
    vertical_extent_start = None
    vertical_extent_end = None
    x = None
    y = None
    fwhm_x = None
    fwhm_y = None
    photon_energy = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._report = "intensityReport"
        self._image_shape = None  # placeholder

    def stage(self):
        pass

    def describe(self):
        res = super().describe()

        num_points = int(self.connection.data["models"]["intensityReport"]["photonEnergyPointCount"])
        res[self.image.name].update(dict(shape=(num_points,)))

        return res

    def trigger(self, *args, **kwargs):
        logger.debug(f"Custom trigger for {self.name}")

        self.connection.data["report"] = self._report

        date = datetime.datetime.now()
        self._assets_dir = date.strftime("%Y/%m/%d")
        self._result_file = f"{new_uid()}.dat"

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
            Path(self._resource_document["root"]) / Path(self._resource_document["resource_path"])
        )

        start_time = time.monotonic()
        self.connection.run_simulation()
        self.duration.put(time.monotonic() - start_time)

        datafile = self.connection.get_datafile()

        with open(sim_result_file, "wb") as f:
            f.write(datafile)

        ndim = 1
        ret = read_srw_file(sim_result_file, ndim=ndim)
        self._resource_document["resource_kwargs"]["ndim"] = ndim

        def update_components(_data):
            self.flux.put(_data["flux"])
            self.mean.put(_data["mean"])

        update_components(ret)

        datum_document = self._datum_factory(datum_kwargs={})
        self._asset_docs_cache.append(("datum", datum_document))

        self.image.put(datum_document["datum_id"])

        self._resource_document = None
        self._datum_factory = None

        logger.debug(f"\nReport for {self.name}: {self.connection.data['report']}\n")

        return NullStatus()

    def unstage(self):
        self._resource_document = None
        self._datum_factory = None


class SirepoSignalGrazingAngle(SirepoSignal):
    def set(self, value):
        super().set(value)
        ret = self.parent.connection.compute_grazing_orientation(self._sirepo_dict)
        # State is added to the ret dict from compute_grazing_orientation and we
        # want to make sure the vectors are updated properly every time the
        # grazing angle is updated.
        ret.pop("state")
        # Update vector components
        for cpt in [
            "normalVectorX",
            "normalVectorY",
            "normalVectorZ",
            "tangentialVectorX",
            "tangentialVectorY",
        ]:
            getattr(self.parent, cpt).put(ret[cpt])
        return NullStatus()


class SirepoSignalCRL(SirepoSignal):
    def set(self, value):
        super().set(value)
        ret = self.parent.connection.compute_crl_characteristics(self._sirepo_dict)
        # State is added to the ret dict from compute_crl_characteristics and we
        # want to make sure the crl element is updated properly when parameters are changed.
        ret.pop("state")
        # Update crl element
        for cpt in ["absoluteFocusPosition", "focalDistance"]:
            getattr(self.parent, cpt).put(ret[cpt])
        return NullStatus()


class SirepoSignalCrystal(SirepoSignal):
    def set(self, value):
        super().set(value)
        ret = self.parent.connection.compute_crystal_orientation(self._sirepo_dict)
        # State is added to the ret dict from compute_crystal_orientation and we
        # want to make sure the crystal element is updated properly when parameters are changed.
        ret.pop("state")
        # Update crystal element
        for cpt in [
            "dSpacing",
            "grazingAngle",
            "nvx",
            "nvy",
            "nvz",
            "outframevx",
            "outframevy",
            "outoptvx",
            "outoptvy",
            "outoptvz",
            "psi0i",
            "psi0r",
            "psiHBi",
            "psiHBr",
            "psiHi",
            "psiHr",
            "tvx",
            "tvy",
        ]:
            getattr(self.parent, cpt).put(ret[cpt])
        return NullStatus()


SimplePropagationConfig = namedtuple(
    "PropagationConfig",
    "resize_before resize_after precision propagator_type "
    + "fourier_resize hrange_mod hres_mod vrange_mod vres_mod",
)


class PropagationConfig(SimplePropagationConfig):
    read_attrs = list(SimplePropagationConfig._fields)
    component_names = SimplePropagationConfig._fields

    def read(self):
        read_attrs = self.read_attrs
        propagation_read = OrderedDict()
        for field in read_attrs:
            propagation_read[field] = getattr(self, field).read()
        return propagation_read
