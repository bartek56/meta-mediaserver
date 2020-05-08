SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pcmanfm.service"


do_install_append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/pcmanfm.service ${D}${systemd_system_unitdir}
}

FILES_${PN} += "${systemd_system_unitdir}/pcmanfm.service"

