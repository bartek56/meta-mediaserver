SUMMARY = "DHCP client daemon service"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://dhcpcd.service"

inherit systemd

SYSTEMD_SERVICE:${PN} = "dhcpcd.service"

do_install:append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/dhcpcd.service ${D}${systemd_unitdir}/system
}

FILES:${PN} += "${systemd_system_unitdir}/dhcpcd.service"

