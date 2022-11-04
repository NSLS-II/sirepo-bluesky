===============
Release History
===============

v0.5.0 (2022-11-04)
-------------------
This is a major release dropping support of Python 3.7 and adding support of
new simulation types.

Applications
............
- Added support for the MAD-X App in Sirepo via detector & flyer API.
  Corresponding simulation examples were added too (sim_id=00000001 and
  00000002). The corresponding handler ``MADXFileHandler`` was implemented for
  reading of MAD-X produced files.
- Implemented ``SingleElectronSpectrumReport`` from the Source page of
  Sirepo/SRW.
- Added the ``duration`` component for detectors.
- Implemented the ``stateless-compute`` support for the grazing angle
  orientation. That is necessary to support recalculation of some properties
  which are normally triggered by the JavaScript client side.
- Converted assertions to exceptions throughout the library code.

Tests
.....
- All integrated simulation codes have corresponging extensive tests (`pytest
  <https://docs.pytest.org/>`_ framework).

Examples
........
- Updated the preparation scripts for the detector and flyer environments to
  make them more consistent.
- Save all test/example data to ``/tmp/sirepo-bluesky-data/``.

Documentation
.............
- Made all examples for SRW, Shadow3, and Beam Statistics Report consistent.
- Added a documentation/notebook with an example of the use of MAD-X via
  sirepo-bluesky API.
- Changed the Sphinx theme to `Cloud <https://cloud-sptheme.readthedocs.io>`_.
- Consitent table widths for simulation lists for different simulation codes.
- Fixed the version string in the published documentation at
  nsls-ii.github.io/sirepo-bluesky.

Scripts/services
................
- Added support for persistent location for the Sirepo database of simulations.
- Using the ``radiasoft/sirepo:20220806.215448`` version of the Sirepo Docker
  image (support of newer images will be added in the following release).
- Added an example systemd unit for ``sirepo.service``.

CI improvements
...............
- Added checks whether the Sirepo container is running before executing the
  tests.
- Using ``mamba`` for faster installation.
- Uploading docs artifacts for each CI run (to allow inspection of the
  documentation draft before publishing it).


v0.4.3 (2021-12-17)
-------------------
- Major rework of the Sphinx documentation with a few automatically rendered
  Jupyter notebooks with examples and better installation instructions.

v0.4.2 (2021-12-13)
-------------------
- Added CI configs to build and publish Sphinx documentation.
- Updated badges in the ``README.rst`` file (GHA workflows status, PyPI, and
  conda-forge releases).
- Updated documentation with a list of custom SRW and Shadow3 simulations.
- Updated NSLS-II TES SRW and Shadow3 examples (``00000002``) to run faster and
  updated validations in the corresponding tests.
- Added a timing test for the ``BeamStatisticsReport`` (Sirepo/Shadow app).
- Updated versioneer's configuration (`python/cpython#28292
  <https://github.com/python/cpython/pull/28292>`_,
  `https://bugs.python.org/issue45173 <https://bugs.python.org/issue45173>`_).

v0.4.1 (2021-11-10)
-------------------
In this release, we addressed some shortcomings of the granular ophyd objects:

- Generalized classes to work with both ``srw`` and ``shadow`` simulation codes.
- Added JSON components for all "detector" classes.
- Added a class to instantiate the ``BeamStatisticsReport`` as an ophyd
  detector and add thorough integration tests.
- Fixed the issue with the last file from a scan being used for all steps of the
  scan.
- Cleaned up the code from unused comments.
- Improved testing coverage and better handling of the results directories.

Packaging/CI
............
- Removed the upper pin of PyQt5.
- Added linting GHA workflow.

v0.4.0 (2021-10-11)
-------------------
- Refactored the code to use an ophyd object per optical element.
- In addition to the existing ``docker`` to start Sirepo server, this update
  also enabled tests with ``podman``.
- Added the NSLS-II TES beamline examples and test data for SRW and Shadow
  codes.

v0.3.1 (2021-09-22)
-------------------
Various CI updates:

- Use ``testuser`` in auth.db.
- Remove TravisCI config.
- Update scripts to start sirepo and mongo with Docker.

v0.3.0 (2021-08-17)
-------------------
- add support and tests for Shadow simulations
- add support for accessing Sirepo's ``simulation-list``

v0.2.0 (2021-04-22)
-------------------
- add support for latest radiasoft/sirepo:beta Docker images
- update for compatibility with databroker v1.x.x
- fix tests

v0.1.0 (2020-09-02)
-------------------
Working version with multiple flyers.

v0.0.2 (2020-03-02)
-------------------
N/A

v0.0.1 - Initial Release (2020-03-02)
-------------------------------------
Initial release of the installable library.
