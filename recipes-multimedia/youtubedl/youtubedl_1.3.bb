SUMMARY = "Youtube_dl script"
HOMEPAGE = "https://github.com/bartek56/youtubedl-web"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "python3 python-mutagen python-yt-dlp metadata-mp3 (= ${PV}) ffmpeg"

SRC_URI="https://raw.githubusercontent.com/bartek56/youtubedl-web/master/Common/YouTubeManager.py \
         file://youtubedl.service \
         file://youtubedl.timer \
         file://youtubedl.ini \
"
inherit systemd

SRC_URI[sha256sum] = "eab1dfefabccd1c33e05497034e5d9a86dcc1a17a61469cda484ae3f9c9f2888"

SYSTEMD_PACKAGES = "${PN}"

do_install(){
    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/YouTubeManager.py ${D}/opt

    install -d ${D}/${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.service ${D}/${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.timer ${D}/${systemd_system_unitdir}

    install -d ${D}/${sysconfdir}/mediaserver
    install -m 0777 ${WORKDIR}/youtubedl.ini ${D}/${sysconfdir}/mediaserver
}


FILES:${PN} += "/opt/YouTubeManager.py"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.service"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.timer"
FILES:${PN} += "${sysconfdir}/mediaserver/youtubedl.ini"
