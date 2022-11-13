SUMMARY = "Youtube_dl script"
HOMEPAGE = "https://github.com/bartek56/LinuxEmbedded"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "python3 python-mutagen python-youtubedl metadata-mp3 ffmpeg"
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


FILES:${PN} += "/opt/downloadFromYoutube.py"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.service"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.timer"
FILES:${PN} += "${sysconfdir}/mediaserver/youtubedl.ini"
