SUMMARY = "Youtube_dl script"
HOMEPAGE = "https://github.com/bartek56/LinuxEmbedded"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "python python-mutagen python-youtubedl"
SRC_URI="file://downloadFromYoutube.py \
         file://youtubedl.service \
         file://youtubedl.timer \
         file://youtubedl.ini \
"
inherit systemd

SYSTEMD_PACKAGES = "${PN}"

do_install(){
    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/downloadFromYoutube.py ${D}/opt

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.timer ${D}${systemd_system_unitdir}

    install -d ${D}${sysconfdir}/mediaserver
    install -m 0755 ${WORKDIR}/youtubedl.ini ${D}${sysconfdir}/mediaserver
}


FILES_${PN} += "/opt/downloadFromYoutube.py"
FILES_${PN} += "${systemd_system_unitdir}/youtubedl.service"
FILES_${PN} += "${systemd_system_unitdir}/youtubedl.timer"
FILES_${PN} += "${sysconfdir}/mediaserver/youtubedl.ini"
