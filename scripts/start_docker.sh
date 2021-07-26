#!/bin/bash

month=$(date +"%m")
day=$(date +"%d")
year=$(date +"%Y")

today="${HOME}/tmp/data/${year}/${month}/${day}"

if [ -d "${today}" ]
then
    echo "Directory ${today} exists."
else
    echo "Creating Directory ${today}"
    mkdir -p "${today}"
fi

mkdir -p $HOME/tmp/sirepo-docker-run

ls -l $HOME/tmp

# specify -it or -d on the command line
docker run $1 --init --rm --name sirepo \
       -e SIREPO_AUTH_METHODS=bluesky:guest \
       -e SIREPO_AUTH_BLUESKY_SECRET=bluesky \
       -e SIREPO_SRDB_ROOT=/sirepo \
       -e SIREPO_COOKIE_IS_SECURE=false \
       -p 8000:8000 \
       -v $HOME/tmp/sirepo-docker-run:/sirepo \
       radiasoft/sirepo:beta bash -l -c "sirepo service http"
