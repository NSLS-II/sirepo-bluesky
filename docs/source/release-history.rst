===============
Release History
===============

v0.6.2 (2023-06-09)
-------------------
This is a maintenance release with small API, tests, packaging, and documentation updates.

API
...
- Fixed the ``BeamStatisticsReport``'s default values which cannot be a
  dictionary (discovered when using `bluesky v1.11.0
  <https://github.com/bluesky/bluesky/releases/tag/v1.11.0>`_).

Packaging
.........
- Added ``xraylib`` to the list of requirements as ``shadow3`` does not
  automatically install it, and imports of ``xraylib`` will print the
  information about that missing library, even for irrelevant code (like
  MAD-X). Adding the package as a dependency explicitly silences the messages.

- Remove pinning of the ``urllib3`` package as the issue is resolved on the
  ``vcrpy`` side.

Documentation
.............
- Updated databroker configuration instructions for Windows.
- Removed old API examples.

Tests
.....
- Removed a test for ``BeamStatisticsReport`` for the old API.


v0.6.1 (2023-05-26)
-------------------
This is a maintenance release primarily addressing the packaging, continuous
integration, and testing matters.

API
...
- Fixed the deprecated API call ``bluesky-auth`` -> ``auth-bluesky-login`` to
  authenticate with Sirepo using the _bluesky_ auth method.

Tests
.....
- Recreated `vcrpy <https://vcrpy.readthedocs.io/en/latest/>`_ cassettes for
  the tests using old API (to be deprecated in the future).
- Fixed beam statistics report test.

CI improvements
...............
- Applied `NSLS-II/start-sirepo-action
  <https://github.com/NSLS-II/start-sirepo-action>`_ to start Sirepo in the CI
  workflows (used in other repositories which need Sirepo with predefined
  examples).
- Fixed the Sirepo startup script to use ``radiasoft/sirepo:beta`` docker
  image. The action above uses the script from this repository.
- Added ``workflow_dispatch`` trigger to CI workflows to be able to start them
  manually.

Packaging
.........
- All dependencies, including ``srwpy`` and ``shadow3`` are now installed along
  with ``sirepo-bluesky`` from the same source (either PyPI or conda-forge),
  therefore users do not need to preinstall them.
- Temporary fix for incompatibility between the ``requests`` package and
  ``urllib3`` v2+.

Documentation
.............
- Change Sphinx theme to `furo <https://pradyunsg.me/furo/>`_.
- Update installation instructions.


v0.6.0 (2023-02-23)
-------------------
This is a major release dropping support of `intake
<https://intake.readthedocs.io/en/latest/>`_ and extending support of MAD-X
simulations.

API
...
- Added ``SirepoSignalRO``.
- Removed `intake <https://intake.readthedocs.io/en/latest/>`_ from the code
  base.

Applications
............
- Added support for the MAD-X commands via the API.

Examples
........
- Updated MAD-X simulation examples to better reflect ATF Beamline 1 and
  Beamline 2.

Documentation
.............
- Added axes labels to the Beam Statistics Report plots.
- Fixed minor spelling errors.
- Updated the documentation with the new MAD-X simulation examples
  demonstrating the ``betx``/``bety`` vs. ``s`` distribution plots before and
  after a parameters change, compared to the Sirepo browser-based interface.

Linting/styling
................
- Enforced formatting with `black <https://black.readthedocs.io/en/stable/>`_,
  `flake8 <https://flake8.pycqa.org/en/latest/>`_, and `isort
  <https://pycqa.github.io/isort/>`_ via `pre-commit hook
  <https://pre-commit.com/>`_.

CI improvements
...............
- Updated the linter CI config to run the ``pre-commit`` checks.


v0.5.0 (2022-11-04)
-------------------
This is a major release dropping support of Python 3.7 and adding support of
new simulation types.

Applications
............
- Added support for the MAD-X App in Sirepo via detector & flyer API.
  Corresponding simulation examples were added too (sim_id=00000001 and
  00000002). The corresponding handler ``MADXFileHandler`` was implemented for
  the reading of MAD-X-produced files.
- Implemented ``SingleElectronSpectrumReport`` from the Source page of
  Sirepo/SRW.
- Added the ``duration`` component for detectors.
- Implemented the ``stateless-compute`` support for the grazing angle
  orientation. That is necessary to support the recalculation of some
  properties which are normally triggered by the JavaScript client side.
- Converted assertions to exceptions throughout the library code.

Tests
.....
- All integrated simulation codes have corresponding extensive tests (`pytest
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
- Consistent table widths for simulation lists for different simulation codes.
- Fixed the version string in the published documentation at
  nsls-ii.github.io/sirepo-bluesky.

Scripts/services
................
- Added support for a persistent location for the Sirepo database of
  simulations.
- Using the ``radiasoft/sirepo:20220806.215448`` version of the Sirepo Docker
  image (support of newer images will be added in the following release).
- Added an example systemd unit for ``sirepo.service``.

CI improvements
...............
- Added checks on whether the Sirepo container is running before executing the
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
