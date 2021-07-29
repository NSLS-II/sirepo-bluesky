#!/bin/bash

month=$(date +"%m")
day=$(date +"%d")
year=$(date +"%Y")

today="${HOME}/tmp/data/${year}/${month}/${day}"

docker_image="radiasoft/sirepo:beta"

if [ -d "${today}" ]
then
    echo "Directory ${today} exists."
else
    echo "Creating Directory ${today}"
    mkdir -p "${today}"
fi

ls -l $HOME/tmp

docker pull ${docker_image}

docker images

# specify -it or -d on the command line
docker run $1 --init --rm --name sirepo \
       -e SIREPO_AUTH_METHODS=bluesky:guest \
       -e SIREPO_AUTH_BLUESKY_SECRET=bluesky \
       -e SIREPO_SRDB_ROOT=/sirepo \
       -e SIREPO_COOKIE_IS_SECURE=false \
       -p 8000:8000 \
       -v $PWD/sirepo_bluesky/tests/SIREPO_SRDB_ROOT:/SIREPO_SRDB_ROOT:ro,z \
       ${docker_image} bash -l -c "mkdir -v -p /sirepo/ && cp -Rv /SIREPO_SRDB_ROOT/* /sirepo/ && sirepo service http"
