==============
sirepo-bluesky
==============

.. image:: https://img.shields.io/travis/NSLS-II/sirepo-bluesky.svg
        :target: https://travis-ci.org/NSLS-II/sirepo-bluesky

.. image:: https://img.shields.io/pypi/v/sirepo-bluesky.svg
        :target: https://pypi.python.org/pypi/sirepo-bluesky


Sirepo-Bluesky interface

* Free software: 3-clause BSD license
* Documentation: (COMING SOON!) https://NSLS-II.github.io/sirepo-bluesky.

Features
--------

* TODO

Purpose:
--------

An attempt to integrate Sirepo/SRW simulations with Bluesky/Ophyd.

Based on this Sirepo simulation that can be downloaded in the next section:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/basic_beamline.png

Prepare a local Sirepo server:
------------------------------

-  Install Sirepo using Vagrant/VirtualBox following the `instructions`_
   (you will need to install `VirtualBox`_ and `Vagrant`_)
-  After the successful installation start the VM with ``vagrant up``
   and ssh to it with ``vagrant ssh``
-  Run the following command to start Sirepo with the Bluesky interface
   (``bluesky`` is a "secret" key used on both server and client sides,
   and the ``SIREPO_FEATURE_CONFIG_SIM_TYPES=srw`` part is optional if
   you run Sirepo directly on a Linux/Mac machine and only have SRW
   installed):

.. code:: bash

   SIREPO_FEATURE_CONFIG_SIM_TYPES=srw SIREPO_AUTH_METHODS=bluesky:guest SIREPO_AUTH_BLUESKY_SECRET=bluesky sirepo service http

-  In your browser, go to http://10.10.10.10:8000/srw, click the
   ":cloud: Import" button in the right-upper corner and upload the
   `archive`_ with the simulation stored in this repo
-  You should be redirected to the address like
   http://10.10.10.10:8000/srw#/source/IKROlKfR
-  Grab the last 8 alphanumeric symbols (``IKROlKfR``), which represent
   a UID for the simulation we will be working with in the next section.

You can also consider running a Docker container:

.. code:: bash

   docker run -it --rm -e SIREPO_AUTH_METHODS=bluesky:guest -e SIREPO_AUTH_BLUESKY_SECRET=bluesky -e SIREPO_SRDB_ROOT=/sirepo -e SIREPO_COOKIE_IS_SECURE=false -p 8000:8000 -v $HOME/tmp/sirepo-docker-run:/sirepo radiasoft/sirepo:beta /home/vagrant/.pyenv/shims/sirepo service http

Prepare Bluesky and trigger a simulated Sirepo detector:
--------------------------------------------------------

-  (OPTIONAL) Make sure you have `mongodb`_ installed and the service is
   running (see `local.yml`_ for details)
-  Create conda environment:

.. code:: bash

   git clone https://github.com/NSLS-II/sirepo-bluesky/
   cd sirepo-bluesky/
   conda create -n sirepo_bluesky python=3.6 -y
   conda activate sirepo_bluesky
   pip install -r requirements.txt

-  Start ``ipython`` and run the following where ``sim_id``
   which is the UID for the simulation we are working with:

.. code:: py

   from sirepo_bluesky import RE, ROOT_DIR, db
   import sirepo_bluesky.sirepo_detector as sd
   import bluesky.plans as bp
   sirepo_det = sd.SirepoDetector(sim_id='IKROlKfR', reg=db.reg)
   sirepo_det.select_optic('Aperture')
   param1 = sirepo_det.create_parameter('horizontalSize')
   param2 = sirepo_det.create_parameter('verticalSize')
   sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
   sirepo_det.configuration_attrs = ['horizontal_extent',
                                     'vertical_extent',
                                     'shape']

.. code:: py

   RE(bp.grid_scan([sirepo_det],
                   param1, 0, 1, 10,
                   param2, 0, 1, 10,
                   True))

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/sirepo_bluesky_grid.png

-  Get the data:

.. code:: py

   import matplotlib.pyplot as plt
   hdr = db[-1]
   imgs = list(hdr.data('sirepo_det_image'))
   cfg = hdr.config_data('sirepo_det')['primary'][0]
   hor_ext = cfg['{}_horizontal_extent'.format(sirepo_det.name)]
   vert_ext = cfg['{}_vertical_extent'.format(sirepo_det.name)]
   plt.imshow(imgs[21], aspect='equal', extent=(*hor_ext, *vert_ext))

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/sirepo_bluesky.png

To view single-electron spectrum report (**Hint:** use a different
``sim_id``, e.g. for the NSLS-II CHX beamline example):

.. code:: py

   from sirepo_bluesky import RE, ROOT_DIR, db
   import sirepo_bluesky.sirepo_detector as sd
   import bluesky.plans as bp
   sirepo_det = sd.SirepoDetector(sim_id='8GJJWLFh', reg=db.reg, source_simulation=True)
   sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
   sirepo_det.configuration_attrs = ['horizontal_extent',
                                     'vertical_extent',
                                     'shape']

.. code:: py

   RE(bp.count([sirepo_det]))

.. code:: py

   import matplotlib.pyplot as plt
   hdr = db[-1]
   imgs = list(hdr.data('sirepo_det_image'))
   plt.plot(imgs[-1])

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/spectrum.png

Use a simulated Sirepo Flyer to run multiple simulations
--------------------------------------------------------

- Coming soon!

.. _instructions: https://github.com/radiasoft/sirepo/wiki/Development
.. _VirtualBox: https://www.virtualbox.org/
.. _Vagrant: https://www.vagrantup.com/
.. _archive: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/examples/basic.zip
.. _mongodb: https://docs.mongodb.com/manual/tutorial/install-mongodb-on-os-x/
.. _local.yml: https://github.com/NSLS-II/sirepo-bluesky/blob/documentation/examples/local.yml