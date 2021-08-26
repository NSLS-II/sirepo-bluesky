#!/bin/bash

# set -vxeuo pipefail
set -e

error_msg="Specify '-it' or '-d' on the command line as a first argument."

arg="${1:-}"

if [ -z "${arg}" ]; then
    echo "${error_msg}"
    exit 1
elif [ "${arg}" != "-it" -a "${arg}" != "-d" ]; then
    echo "${error_msg} Specified argument: ${arg}"
    exit 2
fi

unset cmd _cmd docker_image SIREPO_DOCKER_CONTAINER_ID

month=$(date +"%m")
day=$(date +"%d")
year=$(date +"%Y")

today="${HOME}/tmp/data/${year}/${month}/${day}"

if [ -d "${today}" ]; then
    echo "Directory ${today} exists."
else
    echo "Creating Directory ${today}"
    mkdir -p "${today}"
fi

docker_image="radiasoft/sirepo:beta"

docker pull ${docker_image}

docker images

in_docker_cmd="mkdir -v -p /sirepo/ && cp -Rv /SIREPO_SRDB_ROOT/* /sirepo/ && sirepo service http"
cmd="docker run ${arg} --init --rm --name sirepo \
       -e SIREPO_AUTH_METHODS=bluesky:guest \
       -e SIREPO_AUTH_BLUESKY_SECRET=bluesky \
       -e SIREPO_SRDB_ROOT=/sirepo \
       -e SIREPO_COOKIE_IS_SECURE=false \
       -p 8000:8000 \
       -v $PWD/sirepo_bluesky/tests/SIREPO_SRDB_ROOT:/SIREPO_SRDB_ROOT:ro,z \
       ${docker_image} bash -l -c \"${in_docker_cmd}\""

echo -e "Command to run:\n\n${cmd}\n"
if [ "${arg}" == "-d" ]; then
    SIREPO_DOCKER_CONTAINER_ID=$(eval ${cmd})
    export SIREPO_DOCKER_CONTAINER_ID
    echo "Container ID: ${SIREPO_DOCKER_CONTAINER_ID}"
    docker ps -a
    docker logs ${SIREPO_DOCKER_CONTAINER_ID}
else
    eval ${cmd}
fi
