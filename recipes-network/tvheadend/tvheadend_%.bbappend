SUMMARY = "TvHeadEnd service"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://tvheadend.service"

do_install:append() {
        install -d ${D}${systemd_unitdir}/system
        install -m 0644 ${WORKDIR}/tvheadend.service ${D}${systemd_unitdir}/system
}

FILES:${PN} += "/lib/systemd/system/tvheadend.service"
