#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(realpath "$SCRIPT_DIR/../../..")"
PROJECT_SOURCES="$PROJECT_DIR/sources"
BUILD_CONF="$PROJECT_DIR/build/conf"

clone_repo() {
    local url="$1"
    local branch="$2"
    local destination="$3"

    if [ -d "$destination/.git" ]; then
        echo "Already exists: $destination"
    else
        echo "Cloning: $url"
        git clone -b "$branch" "$url" "$destination"
    fi
}

copy_if_not_exists() {
    local source="$1"
    local destination="$2"

    if [ -f "$destination" ]; then
        echo "Already exists: $destination"
    else
        echo "Copying: $source -> $destination"
        mkdir -p "$(dirname "$destination")"
        cp "$source" "$destination"
    fi
}

mkdir -p "$PROJECT_SOURCES"

clone_repo https://git.yoctoproject.org/poky kirkstone "$PROJECT_SOURCES/poky"
clone_repo https://github.com/meta-qt5/meta-qt5 kirkstone "$PROJECT_SOURCES/meta-qt5"
clone_repo https://git.openembedded.org/meta-openembedded kirkstone "$PROJECT_SOURCES/meta-openembedded"
clone_repo https://git.yoctoproject.org/meta-virtualization kirkstone "$PROJECT_SOURCES/meta-virtualization"
clone_repo https://github.com/agherzan/meta-raspberrypi kirkstone "$PROJECT_SOURCES/meta-raspberrypi"
clone_repo https://github.com/bartek56/meta-mediaserver kirkstone "$PROJECT_SOURCES/meta-mediaserver"

copy_if_not_exists \
    "$PROJECT_SOURCES/meta-mediaserver/conf/yocto_conf/bblayers.conf.sample" \
    "$BUILD_CONF/bblayers.conf"

copy_if_not_exists \
    "$PROJECT_SOURCES/meta-mediaserver/conf/yocto_conf/local.conf.base.sample" \
    "$BUILD_CONF/local.conf"

copy_if_not_exists \
    "$PROJECT_SOURCES/meta-mediaserver/conf/docker/docker-compose.yml" \
    "$PROJECT_DIR/docker-compose.yml"

echo
echo "Setup completed successfully."
