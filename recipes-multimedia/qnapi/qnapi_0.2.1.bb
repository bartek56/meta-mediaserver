SUMMARY = "QNapi - download subtitles"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://doc/LICENSE;md5=751419260aa954499f7abaabaa882bbe"

DEPENDS += " qtbase libmediainfo"
RDEPENDS_${PN} += " p7zip" 

SRC_URI = "https://github.com/QNapi/qnapi/releases/download/${PV}/qnapi-${PV}.tar.gz \
           file://qnapi.ini \
           file://downloadSubtitles.py \
           "

do_install_append(){
        install -d ${D}/etc/mediaserver
        install -m 0755 ${WORKDIR}/qnapi.ini ${D}/etc/mediaserver
}

FILES_${PN} += "${systemd_system_unitdir}/*.service"

SRC_URI[md5sum] = "0b45af36bd06ed9b8c1e281719b316af"
SRC_URI[sha256sum] = "48241041eb9a92203885b1083e40a57f4f3a1674036b44d6539aade333d73b69"

inherit qmake5

S = "${WORKDIR}/qnapi-${PV}"

FILES_${PN} += "/etc/mediaserver/qnapi.ini \
  /usr/bin/qnapi \
  /usr/share/icons/hicolor/16x16/apps/qnapi.png \
  /usr/share/icons/hicolor/48x48/apps/qnapi.png \
  /usr/share/icons/hicolor/512x512/apps/qnapi.png \
  /usr/share/icons/hicolor/32x32/apps/qnapi.png \
  /usr/share/icons/hicolor/128x128/apps/qnapi.png \
  /opt/downloadSubtitles.py \
"

