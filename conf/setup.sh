#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(realpath "$SCRIPT_DIR/../../..")"
PROJECT_SOURCES="$PROJECT_DIR/sources"
BUILD_CONF="$PROJECT_DIR/build/conf"
YOCTO_BRANCH="wrynose"
BITBAKE_TAG="yocto-6.0.3"

clone_repo() {
    local url="$1"
    local branch="$2"
    local destination="$3"

    if [ -d "$destination/.git" ]; then
        local current_branch
        git -C "$destination" remote set-url origin "$url"
        current_branch="$(git -C "$destination" symbolic-ref --short HEAD 2>/dev/null || true)"

        if [ "$current_branch" = "$branch" ]; then
            echo "Already exists on $branch: $destination"
        else
            echo "Updating: $destination ($current_branch -> $branch)"
            git -C "$destination" fetch origin "$branch"
            git -C "$destination" checkout -B "$branch" "origin/$branch"
        fi
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

# Wrynose (Yocto 6.0) no longer uses the combined poky repository.  The
# equivalent tree is openembedded-core plus meta-yocto.
clone_repo https://git.openembedded.org/openembedded-core "$YOCTO_BRANCH" "$PROJECT_SOURCES/poky"
# BitBake does not publish per-release branches; Wrynose's BitBake is tracked
# on the upstream master branch.
clone_repo https://git.openembedded.org/bitbake master "$PROJECT_SOURCES/bitbake"
git -C "$PROJECT_SOURCES/bitbake" fetch --tags origin
git -C "$PROJECT_SOURCES/bitbake" checkout --detach "$BITBAKE_TAG"
clone_repo https://git.yoctoproject.org/meta-yocto "$YOCTO_BRANCH" "$PROJECT_SOURCES/meta-yocto"
clone_repo https://github.com/meta-qt5/meta-qt5 "$YOCTO_BRANCH" "$PROJECT_SOURCES/meta-qt5"
clone_repo https://git.openembedded.org/meta-openembedded "$YOCTO_BRANCH" "$PROJECT_SOURCES/meta-openembedded"
clone_repo https://git.yoctoproject.org/meta-virtualization "$YOCTO_BRANCH" "$PROJECT_SOURCES/meta-virtualization"
clone_repo https://github.com/agherzan/meta-raspberrypi "$YOCTO_BRANCH" "$PROJECT_SOURCES/meta-raspberrypi"
clone_repo https://github.com/bartek56/meta-mediaserver "$YOCTO_BRANCH" "$PROJECT_SOURCES/meta-mediaserver"

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
