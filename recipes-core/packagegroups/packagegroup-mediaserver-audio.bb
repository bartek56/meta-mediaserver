SUMMARY = "MediaServer audio packages"
DESCRIPTION = "Audio services, tools, and clients used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    alsa-utils \
    pulseaudio-server \
    pulseaudio-misc \
    pulseaudio-module-dbus-protocol \
    pulseaudio-module-native-protocol-tcp \
    pulseaudio-module-zeroconf-publish \
    pulseaudio-module-console-kit \
    pulseaudio-module-cli \
    pulseaudio-module-bluez5-device \
    pulseaudio-module-bluez5-discover \
    pulseaudio-module-bluetooth-discover \
    pulseaudio-module-bluetooth-policy \
    pulseaudio-module-loopback \
    pulseaudio \
    mpg123 \
    sox \
    espeak \
"
