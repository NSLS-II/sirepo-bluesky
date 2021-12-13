===================================
Preparation
===================================


Installation
-----------------------------

At the command line::

    $ pip install sirepo-bluesky


Starting Docker
-----------------------------

Run a Docker container:

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

or use the convenience script:

.. code:: bash

   bash scripts/start_sirepo.sh -it

  
Starting Mongo
-----------------------------

Accessing the simualted data using Databroker requires us to have Mongo running. Run:

.. code:: bash

   bash scripts/start_mongo.sh -it
