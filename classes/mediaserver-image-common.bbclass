# Common image policy for all MediaServer images.
inherit sdcard_image-rpi

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
