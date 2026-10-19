# Common image policy for all MediaServer images.
inherit sdcard_image-rpi

def _mediaserver_layer_git_dir(d):
    import pathlib
    current = pathlib.Path(d.getVar("FILE")).resolve()
    for directory in (current.parent, *current.parents):
        if (directory / ".git").exists():
            return str(directory)
    return ""

MEDIASERVER_LAYER_GIT_DIR = "${@_mediaserver_layer_git_dir(d)}"

ROOTFS_POSTPROCESS_COMMAND:append = " mediaserver_write_build_info;"

mediaserver_write_build_info() {
    install -d ${IMAGE_ROOTFS}${sysconfdir}/mediaserver
    {
        echo "format=1"
        echo "built_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "build_host=$(hostname -f 2>/dev/null || hostname)"
        echo "machine=${MACHINE}"
        echo "yocto_branch=${LAYERSERIES_CORENAMES}"
        echo "distro=${DISTRO_NAME}"
        echo "distro_version=${DISTRO_VERSION}"
        echo "image=${IMAGE_BASENAME}"
        echo "image_version=${IMAGE_VERSION}"
        echo "source_date_epoch=${SOURCE_DATE_EPOCH}"
        if [ -n "${MEDIASERVER_LAYER_GIT_DIR}" ] && git -C "${MEDIASERVER_LAYER_GIT_DIR}" rev-parse HEAD >/dev/null 2>&1; then
            echo "meta_mediaserver_commit=$(git -C "${MEDIASERVER_LAYER_GIT_DIR}" rev-parse HEAD)"
        else
            echo "meta_mediaserver_commit=unknown"
        fi
    } > ${IMAGE_ROOTFS}${sysconfdir}/mediaserver/build-info
    {
        echo "format=1"
        echo "built_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        for layer in ${BBLAYERS}; do
            layer_name=$(basename "${layer}")
            layer_key=$(printf '%s' "${layer_name}" | tr '[:punct:] ' '_')
            if git -C "${layer}" rev-parse HEAD >/dev/null 2>&1; then
                echo "layer_${layer_key}_commit=$(git -C "${layer}" rev-parse HEAD)"
            else
                echo "layer_${layer_key}_commit=unknown"
            fi
        done
    } > ${IMAGE_ROOTFS}${sysconfdir}/mediaserver/build-layers
    chmod 0644 ${IMAGE_ROOTFS}${sysconfdir}/mediaserver/build-info
    chmod 0644 ${IMAGE_ROOTFS}${sysconfdir}/mediaserver/build-layers
}

# Keep the boot partition size used by the existing product images.  This is
# image layout, not Raspberry Pi machine configuration.
BOOT_SPACE = "131072"
IMAGE_FSTYPES ?= "tar.bz2 ext3 rpi-sdimg"

# Package selection belongs to the MediaServer packagegroups and image
# recipes. This class only carries policy shared by those images.
# These are product image requirements shared by all MediaServer images.
DISTRO_FEATURES:append = " bluez5 bluetooth wifi libpam pam"
DISTRO_FEATURES += "pam libpam"

IMAGE_FEATURES += " package-management ssh-server-openssh hwcodecs allow-empty-password empty-root-password allow-root-login"

GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "pl-pl en-us en-gb"

TOOLCHAIN_HOST_TASK:append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK:remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"
