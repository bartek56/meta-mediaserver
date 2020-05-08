SUMMARY = "TvHeadEnd service"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://tvheadend.service"

do_install_append() {
        install -d ${D}${systemd_unitdir}/system
        install -m 0644 ${WORKDIR}/tvheadend.service ${D}${systemd_unitdir}/system
}

FILES_${PN} += "/lib/systemd/system/tvheadend.service"
