#!/usr/bin/env bash
set -Eeuo pipefail

# Usage:
#   sudo ./flash-sd.sh IMAGE DEVICE SIZE
#   sudo ./flash-sd.sh IMAGE DEVICE --fill
#
# Examples:
#   sudo ./flash-sd.sh image.rpi-sdimg /dev/mmcblk0 16G
#   sudo ./flash-sd.sh image.rpi-sdimg /dev/sdb 8G
#   sudo ./flash-sd.sh image.rpi-sdimg /dev/mmcblk0 --fill
#
# SIZE uses binary units:
#   16G = 16 GiB
#   2048M = 2048 MiB
#   16GiB = 16 GiB

ROOTFS_PARTITION=2

usage() {
    cat <<'EOF'
Usage:
  sudo ./flash-sd.sh IMAGE DEVICE SIZE
  sudo ./flash-sd.sh IMAGE DEVICE --fill

Arguments:
  IMAGE     Path to the Yocto .rpi-sdimg image
  DEVICE    Whole SD card device, e.g. /dev/mmcblk0 or /dev/sdb
  SIZE      Target rootfs partition size, e.g. 16G, 8G, 2048M
  --fill    Expand rootfs to use the remaining space on the SD card

SIZE is the TOTAL rootfs partition size, not the additional space.
Units are binary: 1G = 1 GiB, 1M = 1 MiB.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ $# -ne 3 ]]; then
    usage
    exit 1
fi

IMAGE=$1
DEVICE=$2
TARGET_SIZE=$3

[[ $EUID -eq 0 ]] || die "Run as root: sudo $0 ..."
[[ -f "$IMAGE" ]] || die "Image not found: $IMAGE"
[[ -b "$DEVICE" ]] || die "Not a block device: $DEVICE"

# Only whole disks are accepted.
[[ "$(lsblk -dn -o TYPE "$DEVICE")" == "disk" ]] ||
    die "DEVICE must be a whole disk, not a partition."

for cmd in dd parted partprobe lsblk blockdev \
           e2fsck resize2fs udevadm; do
    command -v "$cmd" >/dev/null ||
        die "Required command not found: $cmd"
done

# Determine the partition device name.
if [[ "$DEVICE" =~ [0-9]$ ]]; then
    ROOTFS="${DEVICE}p${ROOTFS_PARTITION}"
else
    ROOTFS="${DEVICE}${ROOTFS_PARTITION}"
fi

# Parse decimal size: 4G = 4 GB, 2048M = 2048 MB.
parse_size() {
    local value=$1
    local number unit multiplier

    if [[ "$value" =~ ^([0-9]+)([KMGTP])([iI]?[bB])?$ ]]; then
        number=${BASH_REMATCH[1]}
        unit=${BASH_REMATCH[2]}

        case "$unit" in
            K) multiplier=1000 ;;
            M) multiplier=1000000 ;;
            G) multiplier=1000000000 ;;
            T) multiplier=1000000000000 ;;
            P) multiplier=1000000000000000 ;;
            *) return 1 ;;
        esac

        printf '%s\n' "$((number * multiplier))"
    else
        return 1
    fi
}

# Verify that the image is a raw DOS/MBR disk image.
parted -sm "$IMAGE" unit s print >/dev/null 2>&1 ||
    die "Cannot read partition table in image: $IMAGE"

echo "Image:"
ls -lh "$IMAGE"

echo
echo "Target device:"
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL "$DEVICE"

echo
echo "WARNING: ALL DATA ON $DEVICE WILL BE OVERWRITTEN!"
echo "Image: $IMAGE"
echo "Rootfs: partition $ROOTFS_PARTITION"

if [[ "$TARGET_SIZE" == "--fill" ]]; then
    echo "Mode: use all remaining space on the card"
else
    TARGET_BYTES=$(parse_size "$TARGET_SIZE") ||
        die "Invalid size: $TARGET_SIZE (examples: 16G, 2048M)"

    echo "Target rootfs partition size: $TARGET_SIZE"
fi

echo

read -r -p "Continue? [y/N]: " CONFIRM
[[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]] || die "Cancelled."

# Unmount all existing partitions, starting with the last.
mapfile -t PARTITIONS < <(
    lsblk -lnpo NAME "$DEVICE" | tail -n +2
)

for ((i=${#PARTITIONS[@]}-1; i>=0; i--)); do
    PART="${PARTITIONS[$i]}"

    if findmnt -rn -S "$PART" >/dev/null; then
        echo "Unmounting $PART"
        umount "$PART" || die "Cannot unmount $PART"
    fi
done

# Write the image.
echo
echo "Writing image to $DEVICE ..."
dd if="$IMAGE" of="$DEVICE" bs=4M status=progress conv=fsync

sync

# Reload partition table.
partprobe "$DEVICE"
udevadm settle

[[ -b "$ROOTFS" ]] ||
    die "Rootfs partition not found: $ROOTFS"

# Ensure rootfs is not mounted.
if findmnt -rn -S "$ROOTFS" >/dev/null; then
    umount "$ROOTFS" || die "Cannot unmount $ROOTFS"
fi

# Identify the filesystem.
FSTYPE=$(lsblk -dn -o FSTYPE "$ROOTFS" | xargs)

case "$FSTYPE" in
    ext3|ext4)
        echo "Rootfs filesystem: $FSTYPE"
        ;;
    *)
        die "Expected ext3/ext4 on $ROOTFS, found: ${FSTYPE:-unknown}"
        ;;
esac

# Read partition start and current size in sectors.
PARTITION_INFO=$(
    parted -sm "$DEVICE" unit s print |
        awk -F: -v p="$ROOTFS_PARTITION" '
            $1 == p {
                gsub(/s/, "", $2)
                gsub(/s/, "", $4)
                print $2, $4
            }
        '
)

[[ -n "$PARTITION_INFO" ]] ||
    die "Cannot determine rootfs partition geometry."

read -r START_SECTOR CURRENT_SECTORS <<< "$PARTITION_INFO"

SECTOR_SIZE=$(blockdev --getss "$DEVICE")
DISK_BYTES=$(blockdev --getsize64 "$DEVICE")
DISK_SECTORS=$((DISK_BYTES / SECTOR_SIZE))

# Determine target size.
if [[ "$TARGET_SIZE" == "--fill" ]]; then
    TARGET_SECTORS=$((DISK_SECTORS - START_SECTOR))
else
    TARGET_SECTORS=$((TARGET_BYTES / SECTOR_SIZE))
fi

(( TARGET_SECTORS > 0 )) ||
    die "Target partition size is too small."

(( TARGET_SECTORS >= CURRENT_SECTORS )) ||
    die "Target size is smaller than the original partition. Shrinking is not supported."

(( START_SECTOR + TARGET_SECTORS <= DISK_SECTORS )) ||
    die "Target rootfs size does not fit on the SD card."

NEW_END_SECTOR=$((START_SECTOR + TARGET_SECTORS - 1))

echo
echo "Rootfs start sector: $START_SECTOR"
echo "Current size:        $((CURRENT_SECTORS * SECTOR_SIZE / 1024 / 1024)) MiB"
echo "Target size:         $((TARGET_SECTORS * SECTOR_SIZE / 1024 / 1024)) MiB"

# Resize the partition.
echo
echo "Resizing partition $ROOTFS ..."
parted -s "$DEVICE" unit s resizepart \
    "$ROOTFS_PARTITION" "${NEW_END_SECTOR}s"

partprobe "$DEVICE"
udevadm settle

# Verify partition is not mounted.
if findmnt -rn -S "$ROOTFS" >/dev/null; then
    umount "$ROOTFS" || die "Cannot unmount $ROOTFS"
fi

# Check filesystem before resizing.
echo
echo "Checking filesystem ..."
set +e
e2fsck -f -p "$ROOTFS"
FSCK_STATUS=$?
set -e

# e2fsck: 0 = clean, 1 = errors corrected.
(( FSCK_STATUS == 0 || FSCK_STATUS == 1 )) ||
    die "Filesystem check failed (e2fsck exit code $FSCK_STATUS)."

# Grow ext3/ext4 filesystem to fill its partition.
echo
echo "Resizing filesystem ..."
resize2fs "$ROOTFS"

sync

echo
echo "========================================"
echo "Flash and resize completed successfully."
echo "========================================"
echo
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS "$DEVICE"
