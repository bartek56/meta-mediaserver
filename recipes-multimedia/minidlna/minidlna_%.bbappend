SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/minidlna:"
SRC_URI += "file://minidlna.conf \
            file://minidlna.service"

inherit systemd

do_install_append() {
        install -m 0755 ${WORKDIR}/minidlna.conf ${D}/etc
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/minidlna.service ${D}${systemd_system_unitdir}

}

FILES_${PN} += "${systemd_system_unitdir}/minidlna.service"

