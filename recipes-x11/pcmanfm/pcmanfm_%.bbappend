SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pcmanfm.service"


do_install_append() {
        install -d ${D}${systemd_unitdir}/system
        install -m 0644 ${WORKDIR}/pcmanfm.service ${D}${systemd_unitdir}/system
}

FILES_${PN} += "/lib/systemd/system/pcmanfm.service"
