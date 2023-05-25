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

if [ "${arg}" == "-it" ]; then
    remove_container="--rm"
else
    remove_container=""
fi

SIREPO_SRDB_HOST="${SIREPO_SRDB_HOST:-}"
SIREPO_SRDB_HOST_RO="${SIREPO_SRDB_HOST_RO:-}"
SIREPO_SRDB_GUEST="${SIREPO_SRDB_GUEST:-}"
SIREPO_SRDB_ROOT="${SIREPO_SRDB_ROOT:-'/sirepo'}"

unset cmd _cmd docker_image SIREPO_DOCKER_CONTAINER_ID

year=$(date +"%Y")
month=$(date +"%m")
day=$(date +"%d")

today="${HOME}/tmp/data/${year}/${month}/${day}"

if [ -d "${today}" ]; then
    echo "Directory ${today} exists."
else
    echo "Creating Directory ${today}"
    mkdir -p "${today}"
fi

docker_image_tag=${DOCKER_IMAGE_TAG:-'beta'}  # '20220806.215448' for the older tag
docker_image="radiasoft/sirepo:${docker_image_tag}"
docker_binary=${DOCKER_BINARY:-"docker"}

${docker_binary} pull ${docker_image}

${docker_binary} images

in_docker_cmd=$(cat <<EOF
mkdir -v -p ${SIREPO_SRDB_ROOT} && \
if [ ! -f "${SIREPO_SRDB_ROOT}/auth.db" ]; then \
    cp -Rv /SIREPO_SRDB_ROOT/* ${SIREPO_SRDB_ROOT}/; \
else \
    echo 'The directory exists. Nothing to do'; \
fi && \
sed -i -E \"s;export SIREPO_SRDB_ROOT=\"\(.*\)\";export SIREPO_SRDB_ROOT=\"$SIREPO_SRDB_ROOT\";g\" ~/.radia-run/start && \
cat ~/.radia-run/start && \
~/.radia-run/start
EOF
)

if [ -z "${SIREPO_SRDB_HOST_RO}" ]; then
    if [ -d "$PWD/sirepo_bluesky/tests/SIREPO_SRDB_ROOT" ]; then
        SIREPO_SRDB_HOST_RO="$PWD/sirepo_bluesky/tests/SIREPO_SRDB_ROOT"
    else
        echo "Cannot determine the location of the host SIREPO_SRDB_ROOT dir."
        exit 1
    fi
fi

echo "SIREPO_SRDB_HOST_RO=${SIREPO_SRDB_HOST_RO}"

cmd_start="${docker_binary} run ${arg} --init ${remove_container} --name sirepo \
    -e SIREPO_AUTH_METHODS=bluesky:guest \
    -e SIREPO_AUTH_BLUESKY_SECRET=bluesky \
    -e SIREPO_SRDB_ROOT=${SIREPO_SRDB_ROOT} \
    -e SIREPO_COOKIE_IS_SECURE=false \
    -p 8000:8000 \
    -v $SIREPO_SRDB_HOST_RO:/SIREPO_SRDB_ROOT:ro,z "

cmd_extra=""
if [ ! -z "${SIREPO_SRDB_HOST}" -a ! -z "${SIREPO_SRDB_GUEST}" ]; then
    cmd_extra="-v ${SIREPO_SRDB_HOST}:${SIREPO_SRDB_GUEST}:rw,z "
fi

cmd_end="${docker_image} bash -l -c \"${in_docker_cmd}\""

cmd="${cmd_start}${cmd_extra}${cmd_end}"

echo -e "Command to run:\n\n${cmd}\n"
if [ "${arg}" == "-d" ]; then
    SIREPO_DOCKER_CONTAINER_ID=$(eval ${cmd})
    export SIREPO_DOCKER_CONTAINER_ID
    echo "Container ID: ${SIREPO_DOCKER_CONTAINER_ID}"
    ${docker_binary} ps -a
    ${docker_binary} logs ${SIREPO_DOCKER_CONTAINER_ID}
else
    eval ${cmd}
fi
