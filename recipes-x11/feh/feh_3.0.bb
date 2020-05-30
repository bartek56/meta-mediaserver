LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=cb9e2338a57da8dab5dd61d4df4d2674"
SRCREV = "${PV}"

SRC_URI[md5sum] = "31a2fda452aab6e76b85efc6001a6b53"
SRC_URI="https://feh.finalrewind.org/${PN}-${PV}.tar.bz2 \
         file://screensaver.service \
         file://startScreensaver.sh \
         file://99-calibration.conf \
"

DEPENDS = "curl xserver-xorg xinerama imlib2" 
RDEPENDS_${PN} = "imlib2 bash" 

inherit systemd

SYSTEMD_AUTO_ENABLE = "disable"

P = "${PN}-${PV}"

S = "${WORKDIR}/${P}"

do_install() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0755 ${WORKDIR}/*.service ${D}${systemd_unitdir}/system
    
    install -d ${D}${bindir}
    install -m 0755 ${S}/src/feh ${D}${bindir}
    
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/startScreensaver.sh ${D}/opt/
    
    install -d ${D}/usr/share/X11/xorg.conf.d/
    install -m 0755 ${WORKDIR}/99-calibration.conf ${D}/usr/share/X11/xorg.conf.d/
}

FILES_${PN} += "${systemd_unitdir}/system/*.service"
FILES_${PN} += "opt/startScreensaver.sh"
FILES_${PN} += "${bindir}feh"
FILES_${PN} += "usr/share/X11/xorg.conf.d/99-calibration.conf"



