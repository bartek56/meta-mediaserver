SUMMARY = "Youtube_dl script"
HOMEPAGE = "https://github.com/bartek56/LinuxEmbedded"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "python python-mutagen python-youtubedl"
SRC_URI="file://downloadFromYoutube.py \
         file://youtubedl.service \
         file://youtubedl.timer \
"
inherit systemd

SYSTEMD_PACKAGES = "${PN}"

do_install(){
    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/downloadFromYoutube.py ${D}/opt
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.timer ${D}${systemd_system_unitdir}
}


FILES_${PN} += "/opt/downloadFromYoutube.py"
FILES_${PN} += "/lib/systemd/system/youtubedl.service"
FILES_${PN} += "/lib/systemd/system/youtubedl.timer"

