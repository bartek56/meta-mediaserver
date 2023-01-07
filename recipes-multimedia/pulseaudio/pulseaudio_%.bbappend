SUMMARY = "PulseAudio config"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pulseaudio.service \
            file://system.mediaserver.pa"

inherit systemd 

SYSTEMD_SERVICE:${PN} = "pulseaudio.service"
SYSTEMD_PACKAGES = "${PN}" 

PACKAGECONFIG += "systemd"
PACKAGECONFIG += "dbus"
PACKAGECONFIG += "bluez5"
PACKAGECONFIG += "avahi"
PACKAGECONFIG += "x11"
PACKAGECONFIG += "autospawn-for-root"
EXTRA_OECONF:append=" --enable-esound"

do_install:append() {
        #alsamixer access to pulseaudio
        sed -i 's~load-module module-native-protocol-unix~load-module module-native-protocol-unix auth-anonymous=true~g' ${D}/${sysconfdir}/pulse/system.pa

        install -d ${D}${systemd_unitdir}/system
        install -m 0644 ${WORKDIR}/pulseaudio.service ${D}${systemd_unitdir}/system

        install -d ${D}${sysconfdir}/pulse/system.pa.d
        install -m 0644 ${WORKDIR}/system.mediaserver.pa ${D}${sysconfdir}/pulse/system.pa.d
}

FILES:${PN} += "${sysconfdir}/pulse/system.pa.d/system.mediaserver.pa"
FILES:${PN} += "${systemd_system_unitdir}/pulseaudio.service"
