#!/usr/bin/env bash
set -Eeuo pipefail

# Mount a Raspberry Pi Yocto image read-only.  The image is never written to
# and the loop device is kept in a small state directory until unmounting has
# been verified.

# The script lives in sources/meta-mediaserver/tools, while build/ is at the
# project root next to sources/.
readonly PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
readonly DEFAULT_MACHINE="raspberrypi4-64"
readonly MOUNT_BASE="/mnt/mediaserver-image"
readonly STATE_BASE="/run/mediaserver-image-mount"

usage() {
    cat <<'EOF'
Usage:
  ./tools/mount-image.sh mount [--dry-run] [--read-write] [--increase-rootfs-gb N] [--machine MACHINE] IMAGE_TARGET
  sudo ./tools/mount-image.sh mount [--machine MACHINE] IMAGE_TARGET
  sudo ./tools/mount-image.sh unmount IMAGE_TARGET

IMAGE_TARGET:
  mediaserver-image-base | mediaserver-image-qt6 | mediaserver-image-minimal

The default machine is raspberrypi4-64.  Images are searched below:
  build/tmp/deploy/images/*/

Mount points:
  /mnt/mediaserver-image/IMAGE_TARGET/       root filesystem
  /mnt/mediaserver-image/IMAGE_TARGET/boot/  boot partition

Images and filesystems are mounted read-only by default. Use --read-write
only when modifications are intentional. IMAGE_TARGET must be the same target
that was used for mounting when unmounting.

--dry-run prints the resolved paths and planned operations without requiring
root, an image, or a deploy directory.

With --read-write, a separate IMAGE-migrated.rpi-sdimg copy is created and
mounted. The original image is never modified. Add
--increase-rootfs-gb N to enlarge the migrated image and its root filesystem
by N GB.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

valid_target() {
    case "$1" in
        mediaserver-image-base|mediaserver-image-qt6|mediaserver-image-minimal)
            return 0 ;;
        *)
            return 1 ;;
    esac
}

require_root() {
    [[ $EUID -eq 0 ]] || die "Run as root: sudo $0 ..."
}

image_path() {
    local target=$1
    local image_name="${target}-${MACHINE}.rootfs.rpi-sdimg"
    local deploy_dir="$PROJECT_ROOT/build/tmp/deploy/images"
    local -a matches=()

    [[ -d "$deploy_dir" ]] || die "Deploy directory not found: $deploy_dir"

    while IFS= read -r -d '' candidate; do
        matches+=("$candidate")
    done < <(find "$deploy_dir" -mindepth 2 -maxdepth 2 \
        \( -type f -o -type l \) -name "$image_name" -print0)

    (( ${#matches[@]} == 1 )) || {
        if (( ${#matches[@]} == 0 )); then
            die "Image not found: $image_name (machine: $MACHINE)"
        fi
        printf '%s\n' "Found more than one image named $image_name:" >&2
        printf '  %s\n' "${matches[@]}" >&2
        die "Use a unique deploy directory or select the matching machine."
    }

    local resolved deploy_root
    resolved=$(realpath -e -- "${matches[0]}") || die "Cannot resolve image path."
    deploy_root=$(realpath -e -- "$deploy_dir") || die "Cannot resolve deploy directory."
    case "$resolved" in
        "$deploy_root"/*) ;;
        *) die "Image resolves outside the deploy directory: $resolved" ;;
    esac
    [[ -f "$resolved" && -r "$resolved" ]] || die "Image is not a readable regular file: $resolved"
    printf '%s\n' "$resolved"
}

dry_run_mount() {
    local target=$1
    local image_name="${target}-${MACHINE}.rootfs.rpi-sdimg"
    local deploy_dir="$PROJECT_ROOT/build/tmp/deploy/images"
    local mount_dir="$MOUNT_BASE/$target"
    local state_dir="$STATE_BASE/$target"
    local migrated_image resolved_image
    local -a matches=()

    printf 'Dry run; no changes will be made.\n\n'
    printf 'Project root:       %s\n' "$PROJECT_ROOT"
    printf 'Machine:             %s\n' "$MACHINE"
    if (( READ_WRITE )); then
        printf 'Mount mode:          read-write\n'
    else
        printf 'Mount mode:          read-only\n'
    fi
    if (( ROOTFS_INCREASE_GB > 0 )); then
        printf 'Rootfs increase:     %d GB\n' "$ROOTFS_INCREASE_GB"
    fi
    printf 'Image filename:      %s\n' "$image_name"
    printf 'Deploy directory:    %s\n' "$deploy_dir"

    if [[ -d "$deploy_dir" ]]; then
        while IFS= read -r -d '' candidate; do
            matches+=("$candidate")
        done < <(find "$deploy_dir" -mindepth 2 -maxdepth 2 \
            \( -type f -o -type l \) -name "$image_name" -print0)

        if (( ${#matches[@]} == 0 )); then
            printf 'Image status:        NOT FOUND\n'
        elif (( ${#matches[@]} == 1 )); then
            resolved_image=$(realpath -e -- "${matches[0]}")
            printf 'Image:               %s\n' "$resolved_image"
        else
            printf 'Image status:        AMBIGUOUS (%d matches)\n' "${#matches[@]}"
            printf '  %s\n' "${matches[@]}"
        fi
    else
        printf 'Image status:        deploy directory does not exist\n'
    fi

    if (( READ_WRITE )); then
        if [[ -n "${resolved_image:-}" ]]; then
            migrated_image="${resolved_image%.rpi-sdimg}-migrated.rpi-sdimg"
        else
            migrated_image="IMAGE-migrated.rpi-sdimg"
        fi
        printf 'Read-write copy:     %s\n' "$migrated_image"
    fi

    printf 'Root mount point:    %s\n' "$mount_dir"
    printf 'Boot mount point:    %s/boot\n' "$mount_dir"
    printf 'State file:           %s/state\n' "$state_dir"
    printf '\nPlanned operations:\n'
    if (( READ_WRITE )); then
        printf '  losetup --find --show --partscan IMAGE\n'
        if (( ROOTFS_INCREASE_GB > 0 )); then
            printf '  enlarge IMAGE and partition 2 root filesystem by %d GB\n' "$ROOTFS_INCREASE_GB"
        fi
        printf '  mount -o rw,nosuid,nodev LOOPp2 %s\n' "$mount_dir"
        printf '  mount -o rw,nosuid,nodev,noexec LOOPp1 %s/boot\n' "$mount_dir"
    else
        printf '  losetup --find --show --partscan --read-only IMAGE\n'
        printf '  mount -o ro,nosuid,nodev LOOPp2 %s\n' "$mount_dir"
        printf '  mount -o ro,nosuid,nodev,noexec LOOPp1 %s/boot\n' "$mount_dir"
    fi
    printf '  sync; umount %s/boot; umount %s; losetup --detach LOOP\n' "$mount_dir" "$mount_dir"
}

mount_image() {
    local target=$1
    local state_dir="$STATE_BASE/$target"
    local mount_dir="$MOUNT_BASE/$target"
    local image original_image loop p1 p2 fstype migrated_image rootfs_end_sector
    local rootfs_increase_sectors
    local created_copy=0

    original_image=$(image_path "$target")
    image=$original_image
    if (( READ_WRITE )); then
        echo "WARNING: the image will be mounted read-write:"
        echo "  source: $original_image"
        migrated_image="${original_image%.rpi-sdimg}-migrated.rpi-sdimg"
        [[ ! -e "$migrated_image" ]] ||
            die "Read-write copy already exists: $migrated_image"
        image=$migrated_image
        echo "  copy:   $image"
        echo "The original image will not be modified."
    fi
    [[ ! -e "$state_dir" ]] || die "Image is already mounted or stale state exists: $state_dir"
    [[ ! -e "$mount_dir" ]] || die "Mount point already exists: $mount_dir"

    mkdir -p "$STATE_BASE" "$MOUNT_BASE"
    mkdir "$state_dir" "$mount_dir"

    cleanup_mount() {
        set +e
        mountpoint -q "$mount_dir/boot" && umount "$mount_dir/boot"
        mountpoint -q "$mount_dir" && umount "$mount_dir"
        [[ -n "${loop:-}" ]] && losetup -d "$loop"
        (( created_copy )) && rm -f -- "$image"
        rmdir "$mount_dir" "$state_dir" 2>/dev/null
    }
    trap cleanup_mount ERR

    if (( READ_WRITE )); then
        created_copy=1
        cp --reflink=auto --sparse=always -- "$original_image" "$image"
        if (( ROOTFS_INCREASE_GB > 0 )); then
            echo "Increasing rootfs partition and filesystem by ${ROOTFS_INCREASE_GB} GB..."
            truncate -s "+${ROOTFS_INCREASE_GB}G" -- "$image"
            rootfs_end_sector=$(parted -sm "$image" unit s print |
                awk -F: '$1 == 2 { gsub(/s/, "", $3); print $3 }')
            [[ "$rootfs_end_sector" =~ ^[0-9]+$ ]] ||
                die "Cannot determine rootfs partition end in: $image"
            rootfs_increase_sectors=$((ROOTFS_INCREASE_GB * 1000000000 / 512))
            parted -s -- "$image" unit s resizepart 2 \
                "$((rootfs_end_sector + rootfs_increase_sectors))s"
        fi
        sync
        loop=$(losetup --find --show --partscan -- "$image") ||
            die "Cannot create a read-write loop device for: $image"
    else
        loop=$(losetup --find --show --partscan --read-only -- "$image") ||
            die "Cannot create a read-only loop device for: $image"
    fi

    udevadm settle
    mapfile -t partitions < <(lsblk -lnpo NAME,TYPE "$loop" | awk '$2 == "part" { print $1 }')
    (( ${#partitions[@]} == 2 )) || die "Expected exactly two partitions in $image"
    p1=${partitions[0]}
    p2=${partitions[1]}
    [[ "$(basename -- "$p1")" == "$(basename -- "$loop")p1" ]] || die "Unexpected first partition: $p1"
    [[ "$(basename -- "$p2")" == "$(basename -- "$loop")p2" ]] || die "Unexpected second partition: $p2"

    fstype=$(lsblk -dnro FSTYPE "$p2" | xargs)
    [[ "$fstype" == ext2 || "$fstype" == ext3 || "$fstype" == ext4 ]] ||
        die "Root filesystem must be ext2/ext3/ext4, found: ${fstype:-unknown}"

    if (( READ_WRITE && ROOTFS_INCREASE_GB > 0 )); then
        set +e
        e2fsck -f -p -- "$p2"
        local fsck_status=$?
        set -e
        (( fsck_status == 0 || fsck_status == 1 )) ||
            die "Filesystem check failed (e2fsck exit code $fsck_status)."
        resize2fs -- "$p2" || die "Cannot resize root filesystem: $p2"
    fi

    mkdir "$mount_dir/boot"
    if (( READ_WRITE )); then
        mount -o rw,nosuid,nodev -- "$p2" "$mount_dir"
        mount -o rw,nosuid,nodev,noexec -- "$p1" "$mount_dir/boot"
    else
        mount -o ro,nosuid,nodev -- "$p2" "$mount_dir"
        mount -o ro,nosuid,nodev,noexec -- "$p1" "$mount_dir/boot"
    fi

    {
        printf 'image=%s\n' "$image"
        printf 'loop=%s\n' "$loop"
        printf 'root_partition=%s\n' "$p2"
        printf 'boot_partition=%s\n' "$p1"
    } >"$state_dir/state"
    chmod 600 "$state_dir/state"
    trap - ERR

    if (( READ_WRITE )); then
        echo "Mounted read-write copy: $image"
    else
        echo "Mounted read-only: $image"
    fi
    echo "  root: $mount_dir"
    echo "  boot: $mount_dir/boot"
}

unmount_image() {
    local target=$1
    local state_dir="$STATE_BASE/$target"
    local mount_dir="$MOUNT_BASE/$target"
    local image loop root_partition boot_partition source

    [[ -f "$state_dir/state" ]] || die "No mount state found for: $target"
    [[ -d "$mount_dir" ]] || die "Mount directory is missing: $mount_dir"

    while IFS='=' read -r key value; do
        case "$key" in
            image) image=$value ;;
            loop) loop=$value ;;
            root_partition) root_partition=$value ;;
            boot_partition) boot_partition=$value ;;
            *) die "Invalid state file: $state_dir/state" ;;
        esac
    done <"$state_dir/state"
    [[ -n "${image:-}" && -n "${loop:-}" && -n "${root_partition:-}" && -n "${boot_partition:-}" ]] ||
        die "Incomplete mount state: $state_dir/state"

    if mountpoint -q "$mount_dir"; then
        source=$(findmnt -rn -o SOURCE --target "$mount_dir")
        [[ "$source" == "$root_partition" ]] || die "Unexpected root mount source: $source"
    fi
    if mountpoint -q "$mount_dir/boot"; then
        source=$(findmnt -rn -o SOURCE --target "$mount_dir/boot")
        [[ "$source" == "$boot_partition" ]] || die "Unexpected boot mount source: $source"
    fi
    [[ "$(losetup -j "$image" | cut -d: -f1)" == "$loop" ]] || die "Loop device no longer matches image: $loop"

    sync
    if mountpoint -q "$mount_dir/boot"; then
        umount -- "$mount_dir/boot" || die "Cannot unmount boot filesystem; it may be busy."
        mountpoint -q "$mount_dir/boot" && die "Boot filesystem is still mounted."
    fi
    if mountpoint -q "$mount_dir"; then
        umount -- "$mount_dir" || die "Cannot unmount root filesystem; it may be busy."
        mountpoint -q "$mount_dir" && die "Root filesystem is still mounted."
    fi

    # Do not use findmnt --target here: after the image is unmounted it can
    # report the mount containing the plain directory. Only exact descendants
    # of our mount directory are relevant.
    local -a remaining_mounts=()
    mapfile -t remaining_mounts < <(
        findmnt -rn -o TARGET | awk -v prefix="$mount_dir/" \
            '$0 == prefix || index($0, prefix) == 1 { print }'
    )
    (( ${#remaining_mounts[@]} == 0 )) || {
        printf 'Mounts still present below %s:\n' "$mount_dir" >&2
        printf '  %s\n' "${remaining_mounts[@]}" >&2
        die "A filesystem is still mounted below $mount_dir"
    }

    losetup -d "$loop" || die "Cannot detach loop device $loop; state was preserved."
    if losetup "$loop" >/dev/null 2>&1; then
        die "Loop device is still attached: $loop; state was preserved."
    fi

    rm -f -- "$state_dir/state"
    rmdir -- "$mount_dir/boot" "$mount_dir" "$state_dir"
    echo "Unmounted and detached safely: $target"
    echo "Image: $image"
}

require_command find
require_command findmnt
require_command awk
require_command cut
require_command e2fsck
require_command losetup
require_command lsblk
require_command mount
require_command mountpoint
require_command parted
require_command realpath
require_command resize2fs
require_command sync
require_command truncate
require_command umount
require_command udevadm
require_command xargs

[[ $# -ge 2 ]] || { usage; exit 1; }
ACTION=$1
shift
MACHINE=${MACHINE:-$DEFAULT_MACHINE}
DRY_RUN=0
READ_WRITE=0
ROOTFS_INCREASE_GB=0

case "$ACTION" in
    mount)
        while [[ $# -gt 1 ]]; do
            case "$1" in
                --dry-run)
                    DRY_RUN=1
                    shift
                    ;;
                --read-write|--rw)
                    READ_WRITE=1
                    shift
                    ;;
                --increase-rootfs-gb)
                    [[ $# -ge 3 ]] || { usage; exit 1; }
                    [[ $2 =~ ^[1-9][0-9]*$ ]] ||
                        die "Invalid rootfs increase in GB: $2"
                    ROOTFS_INCREASE_GB=$2
                    READ_WRITE=1
                    shift 2
                    ;;
                --machine)
                    [[ $# -ge 3 ]] || { usage; exit 1; }
                    MACHINE=$2
                    shift 2
                    ;;
                *)
                    usage
                    exit 1
                    ;;
            esac
        done
        [[ $# -eq 1 ]] || { usage; exit 1; }
        TARGET=$1
        valid_target "$TARGET" || die "Unsupported image target: $TARGET"
        if (( DRY_RUN )); then
            dry_run_mount "$TARGET"
        else
            require_root
            mount_image "$TARGET"
        fi
        ;;
    unmount)
        [[ $# -eq 1 ]] || { usage; exit 1; }
        TARGET=$1
        valid_target "$TARGET" || die "Unsupported image target: $TARGET"
        require_root
        unmount_image "$TARGET"
        ;;
    *)
        usage
        exit 1
        ;;
esac
