FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SPLASH_IMAGES:append:rpi = " file://psplash-mediaserver-img.h;outsuffix=mediaserver" 
SRC_URI += " file://psplash-start.service \
             file://psplash-quit.service "

ALTERNATIVE_PRIORITY:psplash-mediaserver[psplash] = "300"

inherit systemd

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE:${PN} = "psplash-start.service"
SYSTEMD_SERVICE:${PN} = "psplash-quit.service"

do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/psplash-start.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/psplash-quit.service ${D}${systemd_system_unitdir}
}

FILES:${PN} += "${systemd_system_unitdir}/psplash-start.service"
FILES:${PN} += "${systemd_system_unitdir}/psplash-quit.service"
FILES:${PN} += "${systemd_system_unitdir}/psplash-systemd.service"

