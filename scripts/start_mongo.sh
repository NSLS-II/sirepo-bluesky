#!/bin/bash

set -vxeuo pipefail

error_msg="Specify '-it' or '-d' on the command line as a first argument."

arg="${1:-}"

if [ -z "${arg}" ]; then
    echo "${error_msg}"
    exit 1
elif [ "${arg}" != "-it" -a "${arg}" != "-d" ]; then
    echo "${error_msg} Specified argument: ${arg}"
    exit 2
fi

docker_image="mongo"

docker pull ${docker_image}
docker images
docker run ${arg} --rm -p 27017:27017 --name mongo ${docker_image}
