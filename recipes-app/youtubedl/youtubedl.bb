SUMMARY = "MediaServer config files and scripts"
HOMEPAGE = "https://github.com/bartek56/LinuxEmbedded"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "python python-mutagen python-youtubedl"
SRC_URI="https://raw.githubusercontent.com/bartek56/LinuxEmbedded/master/configFiles/youtubedl/downloadFromYoutube.py \
         file://youtubedl.service \
         file://youtubedl.timer \
"
inherit systemd

SYSTEMD_PACKAGES = "${PN}"

SRC_URI[md5sum] = "ca1c7ec4b70579e32a8785f4b1558f62"
SRC_URI[sha256sum] = "af65061bfdeb876ec7f2a06b512fd7b3350599659334516501dc07f8ce359d79"

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

