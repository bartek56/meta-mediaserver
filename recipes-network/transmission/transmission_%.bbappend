FILESEXTRAPATHS:prepend := "${THISDIR}/transmission:"

SRC_URI += " \
    file://settings.json \
    file://transmission-daemon.service \
"

do_install:append() {
    install -d ${D}${sysconfdir}/transmission-daemon
    install -m 0644 ${UNPACKDIR}/settings.json  ${D}${sysconfdir}/transmission-daemon/settings.json
    echo '[]' >  ${D}${sysconfdir}/transmission-daemon/queue.json

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/transmission-daemon.service ${D}${systemd_system_unitdir}/transmission-daemon.service
}

FILES:${PN} += "${sysconfdir}/transmission-daemon/settings.json"
FILES:${PN} += "${sysconfdir}/transmission-daemon/queue.json"

SYSTEMD_SERVICE:${PN} = "transmission-daemon.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"
