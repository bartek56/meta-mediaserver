FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SPLASH_IMAGES_append_rpi = " file://psplash-mediaserver-img.h;outsuffix=mediaserver" 
SRC_URI += " file://psplash-start.service \
             file://psplash-quit.service \
             file://01-disable_progress_bar.patch "

ALTERNATIVE_PRIORITY_psplash-mediaserver[psplash] = "300"

inherit systemd

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE_${PN} = "psplash-start.service"
SYSTEMD_SERVICE_${PN} = "psplash-quit.service"

do_install_append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/psplash-start.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/psplash-quit.service ${D}${systemd_system_unitdir}
}

FILES_${PN} += "${systemd_system_unitdir}/psplash-start.service"
FILES_${PN} += "${systemd_system_unitdir}/psplash-quit.service"


