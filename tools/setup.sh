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
    PROJECT_DIR="$(realpath "$SCRIPT_DIR/../../..")"
    if [ ! -d "$PROJECT_DIR/build/conf" ]; then
        echo "Error: Missing required directory: $PROJECT_DIR/build/conf" >&2
        exit 1
    fi

    if [ ! -d "$PROJECT_DIR/sources" ]; then
        echo "Error: Missing required directory: $PROJECT_DIR/sources" >&2
        exit 1
    fi
fi

echo "Project directory: $PROJECT_DIR"


PROJECT_SOURCES="$PROJECT_DIR/sources"
BUILD_CONF="$PROJECT_DIR/build/conf"
YOCTO_BRANCH="wrynose"


# Clone a Git repository if it does not exist, or validate its branch/commit.
#
# Usage:
#   clone_repo URL DESTINATION
#   clone_repo URL DESTINATION BRANCH
#   clone_repo URL DESTINATION BRANCH COMMIT_ID
#
# Behavior:
#   1. URL DESTINATION
#      - Clone the repository if DESTINATION does not exist.
#      - If DESTINATION already exists, skip it without validation or modification.
#
#   2. URL DESTINATION BRANCH
#      - Clone the requested branch if the repository does not exist.
#      - If already on BRANCH, check for local changes and newer remote commits.
#      - Print one OK line if everything is up to date and there are no local changes.
#      - Warn about local changes or differences between local and remote branches.
#      - Do not automatically update the local branch if it is already on BRANCH.
#      - If a branch switch is required, refuse if local changes are present.
#
#   3. URL DESTINATION BRANCH COMMIT_ID
#      - Clone the requested branch and check out COMMIT_ID if the repository does not exist.
#      - If HEAD already matches COMMIT_ID, skip the checkout.
#      - Otherwise, check out COMMIT_ID in detached HEAD state.
#      - Refuse to switch if local changes are present.
#
# Examples:
#   clone_repo https://git.openembedded.org/openembedded-core \
#       "$PROJECT_SOURCES/poky" "$YOCTO_BRANCH"
#
#   clone_repo https://git.openembedded.org/bitbake \
#       "$PROJECT_SOURCES/bitbake" master "$BITBAKE_COMMIT"
#
#   clone_repo https://github.com/bartek56/meta-mediaserver \
#       "$PROJECT_SOURCES/meta-mediaserver" "$YOCTO_BRANCH"

clone_repo() {
    local url="$1"
    local destination="$2"
    local branch="${3:-}"
    local commit_id="${4:-}"
    local current_branch
    local current_commit
    local remote_commit
    local local_changes

    # Validate the number of arguments.
    if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
        echo "Error: Invalid number of arguments." >&2
        echo "Usage: clone_repo URL DESTINATION [BRANCH [COMMIT_ID]]" >&2
        return 1
    fi

    # Two arguments: clone only if the destination does not exist.
    if [ "$#" -eq 2 ]; then
        if [ -d "$destination" ]; then
            echo "Destination already exists, skipping: $destination"
            return 0
        fi

        echo "Cloning: $url -> $destination"
        git clone "$url" "$destination"
        return $?
    fi

    # Clone the requested branch if the repository does not exist.
    if [ ! -d "$destination/.git" ]; then
        echo "Cloning: $url -> $destination (branch: $branch)"

        git clone --branch "$branch" "$url" "$destination" || return 1

        if [ -n "$commit_id" ]; then
            git -C "$destination" checkout --detach "$commit_id"
            return $?
        fi

        return 0
    fi

    # Get the current branch and commit.
    current_commit="$(git -C "$destination" rev-parse HEAD)" || return 1
    current_branch="$(
        git -C "$destination" symbolic-ref --short HEAD 2>/dev/null || true
    )"

    # Check for local changes.
    local_changes="$(git -C "$destination" status --porcelain)" || return 1

    # Four arguments: validate the exact commit.
    if [ -n "$commit_id" ]; then
        if [ "$current_commit" = "$commit_id" ]; then
            if [ -n "$local_changes" ]; then
                echo "Warning: Repository has local changes: $destination" >&2
                git -C "$destination" status --short
            else
                echo "OK: $destination (commit $commit_id)"
            fi
            return 0
        fi
    else
        # Three arguments: validate the current branch.
        if [ "$current_branch" = "$branch" ]; then
            # Fetch remote branch information silently.
            git -C "$destination" fetch -q origin "$branch" || return 1

            remote_commit="$(
                git -C "$destination" rev-parse "origin/$branch"
            )" || return 1

            # Everything is up to date.
            if [ "$current_commit" = "$remote_commit" ] &&
               [ -z "$local_changes" ]; then
                echo "OK: $destination ($branch)"
                return 0
            fi

            # Report local changes.
            if [ -n "$local_changes" ]; then
                echo "Warning: Repository has local changes: $destination" >&2
                git -C "$destination" status --short
            fi

            # Report differences between local and remote branches.
            if [ "$current_commit" != "$remote_commit" ]; then
                if git -C "$destination" merge-base --is-ancestor \
                    "$current_commit" "$remote_commit"; then
                    echo "Warning: Remote branch '$branch' has newer commits: $destination" >&2
                    echo "Local:  $current_commit" >&2
                    echo "Remote: $remote_commit" >&2
                elif git -C "$destination" merge-base --is-ancestor \
                    "$remote_commit" "$current_commit"; then
                    echo "Warning: Local branch '$branch' is ahead of remote: $destination" >&2
                    echo "Local:  $current_commit" >&2
                    echo "Remote: $remote_commit" >&2
                else
                    echo "Warning: Local and remote branches have diverged: $destination" >&2
                    echo "Local:  $current_commit" >&2
                    echo "Remote: $remote_commit" >&2
                fi
            fi

            return 0
        fi
    fi

    # A checkout is required. Refuse to switch if local changes are present.
    if [ -n "$local_changes" ]; then
        echo "Error: Cannot switch branch or commit with local changes: $destination" >&2
        git -C "$destination" status --short
        echo "Commit, stash, or discard the changes before switching." >&2
        return 1
    fi

    # Switch to the requested commit.
    if [ -n "$commit_id" ]; then
        echo "Updating: $destination (commit $current_commit -> $commit_id)"

        git -C "$destination" fetch -q origin "$branch" || return 1
        git -C "$destination" checkout --detach "$commit_id"
        return $?
    fi

    # Switch to the requested branch.
    echo "Updating: $destination ($current_branch -> $branch)"

    git -C "$destination" fetch -q origin "$branch" || return 1
    git -C "$destination" checkout -B "$branch" "origin/$branch"
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

# BitBake does not publish per-release branches; Wrynose's BitBake is tracked
# on the upstream master branch.

clone_repo https://git.openembedded.org/bitbake             "$PROJECT_SOURCES/bitbake"                 master         fae9db3168dbff1b8c76fe9c6726a9687ff97514
clone_repo https://git.openembedded.org/openembedded-core   "$PROJECT_SOURCES/poky"                 "$YOCTO_BRANCH"   0f03c732a0a2d0506b41b1abe60b3f368b2300dc
clone_repo https://git.yoctoproject.org/meta-yocto          "$PROJECT_SOURCES/meta-yocto"           "$YOCTO_BRANCH"   7c25b11156553145fa6b241a2d4f65d94438f804
clone_repo https://github.com/meta-qt5/meta-qt5             "$PROJECT_SOURCES/meta-qt5"             "$YOCTO_BRANCH"   2ca5dfa9403f5454f4bdc702caca00b2cd225a41
clone_repo https://git.openembedded.org/meta-openembedded   "$PROJECT_SOURCES/meta-openembedded"    "$YOCTO_BRANCH"   47d7dbdd10890bbd429bc0cccbe14435c37e5af1
clone_repo https://git.yoctoproject.org/meta-virtualization "$PROJECT_SOURCES/meta-virtualization"  "$YOCTO_BRANCH"   2807579615834a143c8ed453b463f93f43446019
clone_repo https://github.com/agherzan/meta-raspberrypi     "$PROJECT_SOURCES/meta-raspberrypi"     "$YOCTO_BRANCH"   f62c67921474370829d24a4fa01ef88543f3906b
clone_repo https://github.com/bartek56/meta-mediaserver     "$PROJECT_SOURCES/meta-mediaserver"     "$YOCTO_BRANCH"
clone_repo https://github.com/bartek56/MediaServerTests     "$PROJECT_DIR/tests"                        master


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
    "$PROJECT_SOURCES/meta-mediaserver/tools/docker/docker-compose.yml" \
    "$PROJECT_DIR/docker-compose.yml"


copy_if_not_exists \
    "$PROJECT_SOURCES/meta-mediaserver/tools/code-workspace" \
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
