=========================
Installation instructions
=========================

Preparation
-----------

Clone the repository to run the prerequisites:

.. code:: bash

   $ git clone https://github.com/NSLS-II/sirepo-bluesky.git
   $ cd sirepo-bluesky/

.. _Sirepo-startup:

Starting Sirepo
---------------

To make use of the package, we need to run Sirepo as a service. We run Sirepo
using `Docker <https://www.docker.com/>`_ images (`Podman <https://podman.io/>`_
can be used as well) from `DockerHub
<https://hub.docker.com/r/radiasoft/sirepo>`_.  We can start Sirepo locally
using the convenience script:

.. code:: bash

   $ bash scripts/start_sirepo.sh -it

which runs a Docker container as

.. include:: ../../scripts/start_sirepo.sh
   :literal:

.. note::

   One can use the ``-d`` option instead of ``-it`` to run the container in the
   daemon mode.


Starting Mongo
--------------

Accessing the simualted data using Databroker requires us to have Mongo running.
We can similarly run:

.. code:: bash

   $ bash scripts/start_mongo.sh -it

or more explicitly

.. include:: ../../scripts/start_mongo.sh
   :literal:

Likewise, the ``-d`` option can be used instead of ``-it`` to run the container
in the daemon mode.

Configuration of databroker
---------------------------

To to access the collected data with the `databroker
<https://blueskyproject.io/databroker>`_ library, we need to configure it. For
that, please copy the `local.yml
<https://github.com/NSLS-II/sirepo-bluesky/blob/main/examples/local.yml>`_
configuration file to the ``~/.config/databroker/`` directory if using macOS or Linux. For Windows systems,
copy the configuration file to the ``%APPDATA%\databroker`` directory.

.. include:: ../../examples/local.yml
   :literal:


Installation
------------

.. note::

  The installation requires the ``srwpy`` and ``shadow3`` simulation packages to
  be installed to make use of all features of the library. Those packages are
  primarily used by the corresponding handlers to be able to load the data from
  the package-specific formats. The packages are installed automatically when
  the ``sirepo-bluesky`` package is installed via ``pip``:

  - https://pypi.org/project/srwpy
  - https://pypi.org/project/shadow3

  One can also install the packages using ``conda`` from the ``conda-forge``
  channel:

  - https://anaconda.org/conda-forge/srwpy
  - https://anaconda.org/conda-forge/shadow3

Start with creating a conda environment. If you do not have conda installation,
one of the packages from `https://github.com/conda-forge/miniforge
<https://github.com/conda-forge/miniforge>`_ can be used to quickly install the
appropriate conda infrastructure.

At the command line:

.. code:: bash

   $ conda create -n sirepo-bluesky -c conda-forge -y python=3.10
   $ conda activate sirepo-bluesky

Then, to install the released version, run one of the following commands:

.. code:: bash

   $ python3 -m pip install sirepo-bluesky        # to install from PyPI, OR
   $ conda install -c conda-forge sirepo-bluesky  # to install from conda-forge

If you would like to run examples, it is recommended to use the development mode
installation:

.. code:: bash

   $ git clone https://github.com/NSLS-II/sirepo-bluesky.git
   $ cd sirepo-bluesky/
   $ python3 -m pip install -ve .

If you wish to run ``pytest`` tests or build the documentation, please install
the development requirements, such as:

.. code:: bash

   $ python3 -m pip install -r requirements-dev.txt

.. note::

   You may need to install the `Pandoc <https://pandoc.org>`_ library. Please
   follow the instructions at https://pandoc.org/installing.html to install it.

Run tests
.........

.. code:: bash

   $ pytest -vv -s -x --pdb

Build documentation
...................

.. code:: bash

   $ make -C docs/ html
