SUMMARY = "PulseAudio config"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pulseaudio.service \
            file://system.pa \ 
            file://daemon.conf "

inherit systemd 

SYSTEMD_SERVICE_${PN} = "pulseaudio.service"
SYSTEMD_PACKAGES = "${PN}" 

PACKAGECONFIG += "systemd"
PACKAGECONFIG += "dbus"
PACKAGECONFIG += "bluez5"
PACKAGECONFIG += "avahi"
PACKAGECONFIG += "x11"
PACKAGECONFIG += "autospawn-for-root"
EXTRA_OECONF:append=" --enable-esound"

do_install:append() {
        install -d ${D}${systemd_unitdir}/system
        install -m 0755 ${WORKDIR}/pulseaudio.service ${D}${systemd_unitdir}/system

        install -d ${D}${sysconfdir}/pulse
        install -m 0755 ${WORKDIR}/system.pa ${D}${sysconfdir}/pulse
        install -m 0755 ${WORKDIR}/daemon.conf ${D}${sysconfdir}/pulse
}

FILES:${PN} += "${systemd_system_unitdir}/pulseaudio.service"
