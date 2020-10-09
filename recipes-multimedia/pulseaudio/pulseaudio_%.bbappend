SUMMARY = "TvHeadEnd service"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pulseaudio.service"

inherit systemd 

SYSTEMD_SERVICE_${PN} = "pulseaudio.service"
SYSTEMD_PACKAGES = "${PN}" 

do_install_append() {
        install -d ${D}${systemd_unitdir}/system
        install -m 0755 ${WORKDIR}/pulseaudio.service ${D}${systemd_unitdir}/system
}

FILES_${PN} += "${systemd_system_unitdir}/*.service"

