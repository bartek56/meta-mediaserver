FILESEXTRAPATHS_prepend := "${THISDIR}/files:"
SPLASH_IMAGES_append_rpi = " file://psplash-mediaserver-img.h;outsuffix=mediaserver"
ALTERNATIVE_PRIORITY_psplash-mediaserver[psplash] = "300"

inherit systemd

SYSTEMD_PACKAGES = "${PN}"

do_install_append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_unitdir}/system
}

FILES_${PN} += "${systemd_system_unitdir}/*.service"


