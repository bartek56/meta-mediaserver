SUMMARY = "Youtube_dl script"
HOMEPAGE = "https://github.com/bartek56/youtubedl-web"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "python3 python-mutagen python-yt-dlp metadata-mp3 (= ${PV}) ffmpeg"

SRC_URI="git://github.com/bartek56/youtubedl-web;branch=master;protocol=https \
         file://youtubedl.service \
         file://youtubedl.timer \
         file://youtubedl.ini \
"
SRCREV = "${AUTOREV}"

inherit systemd

SRC_URI[sha256sum] = "bc4441984188a32cfc4daa85b0b54dd6f5d12e624545523dc60714d3e6b2a5d5"

SYSTEMD_PACKAGES = "${PN}"

do_install(){
    install -d ${D}/opt/YoutubeDownloader
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/Common/Youtube* ${D}/opt/YoutubeDownloader
    sed -i 's~from .Youtube~from Youtube~g' ${D}/opt/YoutubeDownloader/Youtube*

    install -d ${D}/${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.service ${D}/${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl.timer ${D}/${systemd_system_unitdir}

    #install -d ${D}/${sysconfdir}/mediaserver
    #install -m 0777 ${WORKDIR}/youtubedl.ini ${D}/${sysconfdir}/mediaserver
}


FILES:${PN} += "/opt/YoutubeDownloader/*"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.service"
FILES:${PN} += "${systemd_system_unitdir}/youtubedl.timer"
#FILES:${PN} += "${sysconfdir}/mediaserver/youtubedl.ini"
