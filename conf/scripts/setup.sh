#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -gt 1 ]; then
    echo "Usage: $0 [PROJECT_DIR]" >&2
    exit 1
fi

if [ "$#" -eq 1 ]; then
    if [ ! -d "$1" ]; then
        echo "Error: Project directory does not exist: $1" >&2
        exit 1
    fi

    PROJECT_DIR="$(realpath "$1")"
else
    PROJECT_DIR="$(realpath "$SCRIPT_DIR/../../../..")"
fi

if [ ! -d "$PROJECT_DIR/build/conf" ]; then
    echo "Error: Missing required directory: $PROJECT_DIR/build/conf" >&2
    exit 1
fi

if [ ! -d "$PROJECT_DIR/sources" ]; then
    echo "Error: Missing required directory: $PROJECT_DIR/sources" >&2
    exit 1
fi

echo "Project directory: $PROJECT_DIR"



PROJECT_SOURCES="$PROJECT_DIR/sources"
BUILD_CONF="$PROJECT_DIR/build/conf"
YOCTO_BRANCH="wrynose"
BITBAKE_TAG="yocto-6.0.3"

clone_repo() {
    local url="$1"
    local ref="$2"
    local destination="$3"
    local ref_type="${4:-branch}"
    local current_branch
    local current_tag
    local current_commit
    local target_commit

    if [ "$ref_type" != "branch" ] && [ "$ref_type" != "tag" ]; then
        echo "Error: Unsupported ref type: $ref_type" >&2
        return 1
    fi

    if [ ! -d "$destination/.git" ]; then
        echo "Cloning: $url ($ref_type: $ref)"

        if [ "$ref_type" = "branch" ]; then
            git clone -b "$ref" "$url" "$destination"
        else
            git clone --branch "$ref" --single-branch "$url" "$destination"
        fi

        if [ "$ref_type" = "tag" ]; then
            git -C "$destination" checkout --detach "$ref"
        fi

        return
    fi

    git -C "$destination" remote set-url origin "$url"

    if [ "$ref_type" = "branch" ]; then
        current_branch="$(git -C "$destination" symbolic-ref --short HEAD 2>/dev/null || true)"

        if [ "$current_branch" = "$ref" ]; then
            echo "Already exists on branch $ref: $destination"
            return
        fi

        echo "Updating: $destination ($current_branch -> $ref)"
        git -C "$destination" fetch origin "$ref"
        git -C "$destination" checkout -B "$ref" "origin/$ref"

    else
        current_tag="$(git -C "$destination" describe --tags --exact-match HEAD 2>/dev/null || true)"

        if [ "$current_tag" = "$ref" ]; then
            echo "Already exists on tag $ref: $destination"
            return
        fi

        echo "Updating: $destination ($current_tag -> $ref)"
        git -C "$destination" fetch --tags origin "$ref"
        git -C "$destination" checkout --detach "$ref"
    fi
}

copy_if_not_exists() {
    local source="$1"
    local destination="$2"
    local answer

    if [ ! -f "$destination" ]; then
        echo "Copying: $source -> $destination"
        mkdir -p "$(dirname "$destination")"
        cp "$source" "$destination"
        return
    fi

    if cmp -s "$source" "$destination"; then
        echo "Already synchronized: $destination"
        return
    fi

    echo
    echo "========================================"
    echo "Differences detected:"
    echo "  Source:      $source"
    echo "  Destination: $destination"
    echo "========================================"

    diff -u \
        --label "src: $source" "$source" \
        --label "dst: $destination" "$destination" || true

    echo
    echo "Choose an action:"
    echo "  [s] Copy source      -> destination"
    echo "  [d] Copy destination -> source"
    echo "  [n] Skip"
    echo

    read -r -p "Your choice [s/d/N]: " answer

    case "$answer" in
        [sS])
            cp "$source" "$destination"
            echo "Updated destination: $destination"
            ;;
        [dD])
            cp "$destination" "$source"
            echo "Updated source: $source"
            ;;
        *)
            echo "Skipped: $source <-> $destination"
            ;;
    esac
}

mkdir -p "$PROJECT_SOURCES"

# Wrynose (Yocto 6.0) no longer uses the combined poky repository.  The
# equivalent tree is openembedded-core plus meta-yocto.
clone_repo https://git.openembedded.org/openembedded-core "$YOCTO_BRANCH" "$PROJECT_SOURCES/poky"
# BitBake does not publish per-release branches; Wrynose's BitBake is tracked
# on the upstream master branch.
clone_repo https://git.openembedded.org/bitbake "$BITBAKE_TAG" "$PROJECT_SOURCES/bitbake" tag
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
    "$PROJECT_SOURCES/meta-mediaserver/conf/yocto_conf/local.conf.sample" \
    "$BUILD_CONF/local.conf"

for multiconfig in "$PROJECT_SOURCES"/meta-mediaserver/conf/yocto_conf/multiconfig/*.conf; do
    copy_if_not_exists "$multiconfig" "$BUILD_CONF/multiconfig/$(basename "$multiconfig")"
done

copy_if_not_exists \
    "$PROJECT_SOURCES/meta-mediaserver/conf/docker/docker-compose.yml" \
    "$PROJECT_DIR/docker-compose.yml"


copy_if_not_exists \
    "$PROJECT_SOURCES/meta-mediaserver/conf/scripts/code-workspace" \
    "$PROJECT_DIR/mediaserver.code-workspace"


LINK="$PROJECT_DIR/scripts"
if [ -L "$LINK" ]; then
    echo "Symbolic link to scripts already exists: $LINK"
else
    echo "create link to scripts"
    ln -s "$PROJECT_SOURCES/meta-mediaserver/conf/scripts" "$PROJECT_DIR/scripts"
fi


echo
echo "Setup completed successfully."
