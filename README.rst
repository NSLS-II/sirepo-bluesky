==============
sirepo-bluesky
==============

.. image:: https://img.shields.io/travis/NSLS-II/sirepo-bluesky.svg
        :target: https://travis-ci.org/NSLS-II/sirepo-bluesky

.. image:: https://img.shields.io/pypi/v/sirepo-bluesky.svg
        :target: https://pypi.python.org/pypi/sirepo-bluesky


Sirepo-Bluesky interface

* Free software: 3-clause BSD license
* Citation: 

     Maksim S. Rakitin, Abigail Giles, Kaleb Swartz, Joshua Lynch, Paul Moeller, Robert Nagler,
     Daniel B. Allan, Thomas A. Caswell, Lutz Wiegart, Oleg Chubar, and Yonghua Du
     "Introduction of the Sirepo-Bluesky interface and its application to the optimization problems",
     Proc. SPIE 11493, Advances in Computational Methods for X-Ray Optics V, 1149311 (21 August 2020);
     https://doi.org/10.1117/12.2569000 

Purpose
-------

An attempt to integrate Sirepo/SRW simulations with Bluesky/Ophyd.

Based on this Sirepo simulation that can be downloaded in the next section:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/master/images/basic_beamline.png


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
   docker run -it --init --rm --name sirepo \
          -e SIREPO_AUTH_METHODS=bluesky:guest \
          -e SIREPO_AUTH_BLUESKY_SECRET=bluesky \
          -e SIREPO_SRDB_ROOT=/sirepo \
          -e SIREPO_COOKIE_IS_SECURE=false \
          -p 8000:8000 \
          -v $HOME/tmp/sirepo-docker-run:/sirepo \
          radiasoft/sirepo:beta bash -l -c "sirepo service http"


Prepare Bluesky and trigger a simulated Sirepo detector
-------------------------------------------------------

-  (OPTIONAL) Make sure you have `mongodb`_ installed and the service is
   running (see `local.yml`_ for details)
-  Create a conda environment:

.. code:: bash

   conda create -n sirepo_bluesky python=3.7 -y
   conda activate sirepo_bluesky
   pip install sirepo-bluesky  # a package from PyPI

- Clone this repository to have access to the examples:

.. code:: bash

   git clone https://github.com/NSLS-II/sirepo-bluesky/
   cd sirepo-bluesky/

-  Start ``ipython`` and run the following where ``sim_id`` is the
   UID for the simulation we are working with:

.. code:: py

   %run -i examples/prepare_det_env.py
   import sirepo_bluesky.sirepo_detector as sd
   import bluesky.plans as bp
   sirepo_det = sd.SirepoDetector(sim_id='<sim_id>')
   sirepo_det.select_optic('Aperture')
   param1 = sirepo_det.create_parameter('horizontalSize')
   param2 = sirepo_det.create_parameter('verticalSize')
   sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
   sirepo_det.configuration_attrs = ['horizontal_extent', 'vertical_extent', 'shape']

.. code:: py

   RE(bp.grid_scan([sirepo_det],
                   param1, 0, 1, 10,
                   param2, 0, 1, 10,
                   True))

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/master/images/sirepo_bluesky_grid.png

-  Get the data:

.. code:: py

   hdr = db[-1]
   imgs = list(hdr.data('sirepo_det_image'))
   cfg = hdr.config_data('sirepo_det')['primary'][0]
   hor_ext = cfg['{}_horizontal_extent'.format(sirepo_det.name)]
   vert_ext = cfg['{}_vertical_extent'.format(sirepo_det.name)]
   plt.imshow(imgs[21], aspect='equal', extent=(*hor_ext, *vert_ext))

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/master/images/sirepo_bluesky.png

To view single-electron spectrum report (**Hint:** use a different
``sim_id``, e.g. for the NSLS-II CHX beamline example):

.. code:: py

   %run -i examples/prepare_det_env.py
   import sirepo_bluesky.sirepo_detector as sd
   import bluesky.plans as bp
   sirepo_det = sd.SirepoDetector(sim_id='<sim_id>', reg=db.reg, source_simulation=True)
   sirepo_det.read_attrs = ['image']
   sirepo_det.configuration_attrs = ['photon_energy', 'shape']

.. code:: py

   RE(bp.count([sirepo_det]))

.. code:: py

   hdr = db[-1]
   cfg = hdr.config_data('sirepo_det')['primary'][0]
   energies = cfg['sirepo_det_photon_energy']
   spectrum, = hdr.data('sirepo_det_image')
   plt.plot(energies, spectrum)

You should get something like:

.. image:: https://github.com/NSLS-II/sirepo-bluesky/raw/master/images/spectrum.png


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

    In[13]: hdr = db[-1]
            hdr.table(stream_name='sirepo_flyer')

    Out[13]:
                                  time                    sirepo_flyer_image  \
    seq_num
    1       2020-08-10 07:54:01.426501  ae51b7d7-1a0f-4613-9118-1626b4f89bf0
    2       2020-08-10 07:54:01.426501  14183b1a-03f1-4333-a4a2-b9e16ccdbf29
    3       2020-08-10 07:54:01.426501  2e372fb4-7fe3-47ce-acf8-9af3e2d1acad
    4       2020-08-10 07:54:01.426501  7bea7ace-0be3-4b97-a936-f2cec48cb370
    5       2020-08-10 07:54:01.426501  7e22377b-985c-49d9-aaf4-26c967b1bd22

            sirepo_flyer_shape  sirepo_flyer_mean  sirepo_flyer_photon_energy  \
    seq_num
    1               [250, 896]       3.677965e+13                      4240.0
    2               [250, 546]       9.944933e+13                      4240.0
    3               [250, 440]       1.492891e+14                      4240.0
    4               [252, 308]       2.234285e+14                      4240.0
    5               [252, 176]       3.885947e+14                      4240.0

                              sirepo_flyer_horizontal_extent  \
    seq_num
    1        [-0.0013627376425855513, 0.0013596958174904943]
    2         [-0.001015813953488372, 0.0010120930232558139]
    3        [-0.0009701657458563539, 0.0009701657458563542]
    4        [-0.0008026143790849673, 0.0008026143790849673]
    5        [-0.0005374045801526716, 0.0005312977099236639]

                                 sirepo_flyer_vertical_extent  \
    seq_num
    1         [-0.000249500998003992, 0.00024750499001996017]
    2         [-0.000249500998003992, 0.00024750499001996017]
    3        [-0.00024650698602794426, 0.0002504990019960079]
    4        [-0.0002485029940119762, 0.00025249500998003984]
    5        [-0.00025149700598802393, 0.0002495009980039921]

                      sirepo_flyer_hash_value sirepo_flyer_status  \
    seq_num
    1        d5d6628d50bd65a329717e8ffb942224           completed
    2        d6f8b77048fe6ad48e007cfb776528ad           completed
    3        e5f914471d873f156c31815ab705575f           completed
    4        bf507c942bb67c7191d16968de6ddd5b           completed
    5        1775724d932efa3e0233781465a5a67b           completed

             sirepo_flyer_Aperture_horizontalSize  \
    seq_num
    1                                         0.1
    2                                         0.2
    3                                         0.3
    4                                         0.4
    5                                         0.5

             sirepo_flyer_Aperture_verticalSize  \
    seq_num
    1                                       1.5
    2                                       1.4
    3                                       1.3
    4                                       1.2
    5                                       1.1

             sirepo_flyer_Lens_horizontalFocalLength  \
    seq_num
    1                                              8
    2                                              9
    3                                             10
    4                                             11
    5                                             12

             sirepo_flyer_Obstacle_horizontalSize
    seq_num
    1                                           5
    2                                           4
    3                                           3
    4                                           2
    5                                           1

.. _instructions: https://github.com/radiasoft/sirepo/wiki/Development
.. _VirtualBox: https://www.virtualbox.org/
.. _Vagrant: https://www.vagrantup.com/
.. _archive: https://github.com/NSLS-II/sirepo-bluesky/raw/master/examples/basic.zip
.. _mongodb: https://docs.mongodb.com/manual/tutorial/install-mongodb-on-os-x/
.. _local.yml: https://github.com/NSLS-II/sirepo-bluesky/blob/master/examples/local.yml
