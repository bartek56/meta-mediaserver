FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://transmission-daemon.service \
            file://settings.json \
            "

do_install:append() {
    install -d ${D}/etc/transmission-daemon
    install -m 0644 ${WORKDIR}/settings.json ${D}/etc/transmission-daemon
    install -m 0644 ${WORKDIR}/transmission-daemon.service ${D}${systemd_unitdir}/system

}

FILES:${PN} += "/etc/transmission-daemon/settings.json"


