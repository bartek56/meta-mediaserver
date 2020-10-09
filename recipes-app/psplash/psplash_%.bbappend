FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SPLASH_IMAGES_append_rpi = " file://psplash-mediaserver-img.h;outsuffix=mediaserver" 
SRC_URI += " file://psplash.service"

ALTERNATIVE_PRIORITY_psplash-mediaserver[psplash] = "300"

inherit systemd

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE_${PN} = "psplash.service"

do_install_append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/psplash.service ${D}${systemd_system_unitdir}
}

FILES_${PN} += "${systemd_system_unitdir}/psplash.service"


