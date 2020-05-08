SUMMARY = "DHCP client daemon service"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://dhcpcd.service"

inherit systemd

do_install_append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/dhcpcd.service ${D}${systemd_unitdir}/system
}

FILES_${PN} += "${systemd_system_unitdir}/dhcpcd.service"

