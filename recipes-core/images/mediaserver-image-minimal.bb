include recipes-core/images/core-image-base.bb

inherit sdcard_image-rpi

BOOT_SPACE = "131072"

SUMMARY = "Minimal base system with Snapcast client and PulseAudio"
LICENSE = "MIT"

# Deliberately independent from mediaserver-image-common: that class contains
# the full standard server package set.  This image is a headless Snapcast/
# MPD endpoint and must not inherit GUI, web-server, Docker, or Qt packages.
IMAGE_FSTYPES ?= "tar.bz2 ext3 rpi-sdimg"

NETWORK = " \
    dhcpcd \
    iw \
    wpa-supplicant \
"

TOOLS = " \
    system-configurator \
    configscript \
    snapcast-client \
    vim \
    wget \
    git \
"

# The minimal image is used as a Snapcast/MPD audio endpoint.  MPD on the
# media server can connect to this device using an audio_output of type
# "pulse", so the endpoint needs the PulseAudio daemon and its TCP module.
# Keep this limited to the runtime pieces; the full media-server image adds
# the remaining PulseAudio modules and multimedia services.
PULSE_AUDIO = " \
    pulseaudio \
    pulseaudio-server \
    pulseaudio-module-native-protocol-tcp \
    pulseaudio-module-zeroconf-publish \
"

AUDIO_TOOLS = " \
    alsa-utils-alsamixer \
    alsa-utils-speaker-test \
"

DISTRO_FEATURES:append = " bluez5 bluetooth wifi libpam pam"
DISTRO_FEATURES += "pam libpam"

IMAGE_INSTALL:append = " \
    ${NETWORK} \
    ${TOOLS} \
    ${PULSE_AUDIO} \
    ${AUDIO_TOOLS} \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"

IMAGE_FEATURES += " package-management ssh-server-openssh hwcodecs allow-empty-password empty-root-password allow-root-login"


GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "pl-pl en-us en-gb"
#LOCALE_UTF8_ONLY="1"

TOOLCHAIN_HOST_TASK:append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK:remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"
