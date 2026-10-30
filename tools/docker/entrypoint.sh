#!/usr/bin/env bash
set -e

export OEROOT=/home/builder/yocto-project/sources/poky

PROJECT_DIR=/home/builder/yocto-project
BUILD_DIR="${PROJECT_DIR}/build"

# Initialize the existing build directory shared with the host.
if [ ! -d "${BUILD_DIR}" ]; then
    echo "Error: Build directory does not exist: ${BUILD_DIR}" >&2
    exit 1
fi

if [ ! -w "${BUILD_DIR}" ]; then
    echo "Error: Build directory is not writable: ${BUILD_DIR}" >&2
    echo "Check Docker UID/GID and host directory permissions." >&2
    exit 1
fi

source "${OEROOT}/oe-init-build-env" "${BUILD_DIR}" >/dev/null

if [ "$#" -eq 0 ]; then
    exec bash
fi

exec "$@"
