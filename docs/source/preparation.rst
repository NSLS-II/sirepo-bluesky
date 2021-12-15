===================================
Preparation
===================================


Installation
-----------------------------

At the command line::

    $ pip install sirepo-bluesky

Starting Sirepo
-----------------------------

We can start Sirepo locally using the convenience script 

.. code:: bash

   bash scripts/start_sirepo.sh -it

which runs a Docker container as

.. include:: ../../scripts/start_sirepo.sh
   :literal:

  
Starting Mongo
-----------------------------

Accessing the simualted data using Databroker requires us to have Mongo running. We can similarly run:

.. code:: bash

   bash scripts/start_mongo.sh -it

or more explicitly

.. include:: ../../scripts/start_mongo.sh
   :literal: