SUMMARY = "Youtube_dl script"
HOMEPAGE = "https://github.com/bartek56/youtubedl-web"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "python3 python-mutagen python-yt-dlp metadata-mp3 (= ${PV}) ffmpeg"

SRC_URI="https://raw.githubusercontent.com/bartek56/youtubedl-web/master/Common/YoutubeManager.py \
         file://youtubedl.service \
         file://youtubedl.timer \
         file://youtubedl.ini \
"
SRCREV = "${AUTOREV}"

inherit systemd

SRC_URI[sha256sum] = "bc4441984188a32cfc4daa85b0b54dd6f5d12e624545523dc60714d3e6b2a5d5"

SYSTEMD_PACKAGES = "${PN}"

do_install(){
    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/YoutubeManager.py ${D}/opt

    install -d ${D}/${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.service ${D}/${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.timer ${D}/${systemd_system_unitdir}

    #install -d ${D}/${sysconfdir}/mediaserver
    #install -m 0777 ${WORKDIR}/youtubedl.ini ${D}/${sysconfdir}/mediaserver
}


FILES:${PN} += "/opt/YoutubeManager.py"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.service"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.timer"
#FILES:${PN} += "${sysconfdir}/mediaserver/youtubedl.ini"
