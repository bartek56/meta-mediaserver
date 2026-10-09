SUMMARY = "PulseAudio config"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pulseaudio.service \
            file://system.mediaserver.pa \
            file://99-mediaserver-audio-names.rules"

inherit systemd 

SYSTEMD_SERVICE:${PN} = "pulseaudio.service"
SYSTEMD_PACKAGES = "${PN}" 

PACKAGECONFIG += "systemd"
PACKAGECONFIG += "dbus"
PACKAGECONFIG += "bluez5"
PACKAGECONFIG += "avahi"
PACKAGECONFIG += "x11"
PACKAGECONFIG += "autospawn-for-root"
EXTRA_OECONF:append = " --enable-esound"

do_install:append() {
        # The Raspberry Pi bcm2835 ALSA driver can report spurious POLLOUT
        # wakeups when PulseAudio uses timer scheduling.  This causes audio
        # dropouts when MPD switches between PulseAudio and Snapcast outputs.
        sed -i 's/^load-module module-udev-detect$/load-module module-udev-detect tsched=0/' ${D}/${sysconfdir}/pulse/system.pa

        #alsamixer access to pulseaudio
        sed -i 's~load-module module-native-protocol-unix~load-module module-native-protocol-unix auth-anonymous=true~g' ${D}/${sysconfdir}/pulse/system.pa

        install -d ${D}${systemd_unitdir}/system
        install -m 0644 ${UNPACKDIR}/pulseaudio.service ${D}${systemd_unitdir}/system

        install -d ${D}${sysconfdir}/pulse/system.pa.d
        install -m 0644 ${UNPACKDIR}/system.mediaserver.pa ${D}${sysconfdir}/pulse/system.pa.d

        install -d ${D}${sysconfdir}/udev/rules.d
        install -m 0644 ${UNPACKDIR}/99-mediaserver-audio-names.rules ${D}${sysconfdir}/udev/rules.d
}

FILES:${PN} += "${sysconfdir}/pulse/system.pa.d/system.mediaserver.pa"
FILES:${PN} += "${sysconfdir}/udev/rules.d/99-mediaserver-audio-names.rules"
FILES:${PN} += "${systemd_system_unitdir}/pulseaudio.service"
