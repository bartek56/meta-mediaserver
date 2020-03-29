LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=cb9e2338a57da8dab5dd61d4df4d2674"
SRCREV = "${PV}"

SRC_URI[md5sum] = "31a2fda452aab6e76b85efc6001a6b53"
SRC_URI="https://feh.finalrewind.org/${PN}-${PV}.tar.bz2 \
         file://screensaver.service \
         file://startScreensaver.sh"

DEPENDS = "curl" 
RDEPENDS_${PN} = "imlib2" 

inherit systemd

SYSTEMD_AUTO_ENABLE = "disable"

P = "${PN}-${PV}"

S = "${WORKDIR}/${P}"

do_install() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_unitdir}/system
    install -d ${D}${bindir}
    install -m 0644 ${S}/src/feh ${D}${bindir}
    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/startScreensaver.sh ${D}/opt/
}

FILES_${PN} += "${systemd_unitdir}/system/*.service"
FILES_${PN} += "opt/startScreensaver.sh"
FILES_${PN} += "${bindir}feh"



