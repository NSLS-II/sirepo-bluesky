==============
sirepo-bluesky
==============

.. image:: https://img.shields.io/travis/NSLS-II/sirepo-bluesky.svg
        :target: https://travis-ci.org/NSLS-II/sirepo-bluesky

.. image:: https://img.shields.io/pypi/v/sirepo-bluesky.svg
        :target: https://pypi.python.org/pypi/sirepo-bluesky


Sirepo-Bluesky interface

* Free software: 3-clause BSD license
* Documentation: https://NSLS-II.github.io/sirepo-bluesky.

Purpose
-------

An attempt to integrate Sirepo/SRW simulations with Bluesky/Ophyd.

Based on this Sirepo simulation that can be downloaded in the next section:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/basic_beamline.png


Prepare a local Sirepo server
-----------------------------

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
   "Import" button in the right-upper corner and upload the
   `archive`_ with the simulation stored in this repo
-  You should be redirected to the address like
   ``http://10.10.10.10:8000/srw#/source/IKROlKfR``
-  Grab the last 8 alphanumeric symbols (``IKROlKfR``), which represent
   a UID for the simulation we will be working with in the next section.

You can also consider running a Docker container:

.. code:: bash

   mkdir -p $HOME/tmp/sirepo-docker-run
   docker run -it --rm -e SIREPO_AUTH_METHODS=bluesky:guest -e SIREPO_AUTH_BLUESKY_SECRET=bluesky -e SIREPO_SRDB_ROOT=/sirepo -e SIREPO_COOKIE_IS_SECURE=false -p 8000:8000 -v $HOME/tmp/sirepo-docker-run:/sirepo radiasoft/sirepo:beta /home/vagrant/.pyenv/shims/sirepo service http


Prepare Bluesky and trigger a simulated Sirepo detector
-------------------------------------------------------

-  (OPTIONAL) Make sure you have `mongodb`_ installed and the service is
   running (see `local.yml`_ for details)
-  Create a conda environment:

.. code:: bash

   git clone https://github.com/NSLS-II/sirepo-bluesky/
   cd sirepo-bluesky/
   conda create -n sirepo_bluesky python=3.7 -y
   conda activate sirepo_bluesky
   pip install -e .

-  Start ``ipython`` and run the following where ``sim_id`` is the
   UID for the simulation we are working with:

.. code:: py

   %run -i examples/prepare_det_env.py
   import sirepo_bluesky.sirepo_detector as sd
   import bluesky.plans as bp
   sirepo_det = sd.SirepoDetector(sim_id='<sim_id>', reg=db.reg)
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

   %run -i examples/prepare_det_env.py
   import sirepo_bluesky.sirepo_detector as sd
   import bluesky.plans as bp
   sirepo_det = sd.SirepoDetector(sim_id='<sim_id>', reg=db.reg, source_simulation=True)
   sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
   sirepo_det.configuration_attrs = ['horizontal_extent',
                                     'vertical_extent',
                                     'shape']

.. code:: py

   RE(bp.count([sirepo_det]))

.. code:: py

   hdr = db[-1]
   imgs = list(hdr.data('sirepo_det_image'))
   plt.plot(imgs[-1])

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/spectrum.png


Use a simulated Sirepo Flyer to run multiple simulations
--------------------------------------------------------

- This section is based on the Young's Double Slit Experiment Sirepo example
  that can be found in the wavefront propagation folder on the SRW simulations
  section

- Open the simulation and grab the new UID (the last 8 alphanumeric symbols)

- Start ``ipython`` and run the following:

.. code:: py

    %run -i examples/prepare_flyer_env.py
    import bluesky.plans as bp
    import sirepo_bluesky.sirepo_flyer as sf

- To create 5 different simulations that change 4 parameters at a time:

.. code:: py

    params_to_change = []
    for i in range(1, 6):
        key1 = 'Aperture'
        parameters_update1 = {'horizontalSize': i * .1, 'verticalSize': (16 - i) * .1}
        key2 = 'Lens'
        parameters_update2 = {'horizontalFocalLength': i + 7}
        key3 = 'Obstacle'
        parameters_update3 = {'horizontalSize': 6 - i}
        params_to_change.append({key1: parameters_update1,
                                 key2: parameters_update2,
                                 key3: parameters_update3})

- Create the flyer and run a fly scan where ``sim_id`` is the UID of this
  simulation:

.. code:: py

        sirepo_flyer = sf.SirepoFlyer(sim_id='<sim_id>', server_name='http://10.10.10.10:8000',
                                      root_dir=root_dir, params_to_change=params_to_change,
                                      watch_name='W60')

        RE(bp.fly([sirepo_flyer]))

- Access the data:

.. code:: py

    hdr = db[-1]
    hdr.table(stream_name="sirepo_flyer")

Databroker will return the following information:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/images/flyer_output.PNG

.. _instructions: https://github.com/radiasoft/sirepo/wiki/Development
.. _VirtualBox: https://www.virtualbox.org/
.. _Vagrant: https://www.vagrantup.com/
.. _archive: https://github.com/NSLS-II/sirepo-bluesky/raw/documentation/examples/basic.zip
.. _mongodb: https://docs.mongodb.com/manual/tutorial/install-mongodb-on-os-x/
.. _local.yml: https://github.com/NSLS-II/sirepo-bluesky/blob/documentation/examples/local.yml
