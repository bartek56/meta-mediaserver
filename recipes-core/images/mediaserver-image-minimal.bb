include recipes-core/images/core-image-base.bb

inherit mediaserver-image-common

SUMMARY = "Minimal base system with Snapcast client and PulseAudio"
LICENSE = "MIT"

# This image is a headless Snapcast/MPD endpoint and does not install the
# standard server packagegroups, web-server, Docker, or Qt packages.

NETWORK = " \
    dhcpcd \
    iw \
    wpa-supplicant \
"

TOOLS = " \
    system-configurator \
    configscript-minimal \
    snapcast-client \
    vim \
    wget \
    git \
    motd-status \
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

IMAGE_INSTALL:append = " \
    ${NETWORK} \
    ${TOOLS} \
    ${PULSE_AUDIO} \
    ${AUDIO_TOOLS} \
    ytcast-open \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"
