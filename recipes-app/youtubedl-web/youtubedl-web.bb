SUMMARY = "Youtubedl-web"
HOMEPAGE = "https://github.com/bartek56/LinuxEmbedded"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "python3 python3-flask metadata-mp3"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/youtubedl-web \
           file://youtubedl-web.service \
          "
inherit systemd

SYSTEMD_AUTO_ENABLE = "enable" 
SYSTEMD_SERVICE_${PN} = "youtubedl-web.service"

do_install(){
    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/main.py ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web/static
    install -m 0644 ${WORKDIR}/git/static/* ${D}/opt/youtubedl-web/static

    install -d ${D}/opt/youtubedl-web/templates
    install -m 0644 ${WORKDIR}/git/templates/* ${D}/opt/youtubedl-web/templates

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl-web.service ${D}${systemd_system_unitdir}
}


FILES_${PN} += "${systemd_system_unitdir}/youtubedl-web.service"
FILES_${PN} += "/opt/youtubedl-web/main.py"
FILES_${PN} += "/opt/youtubedl-web/templates"
FILES_${PN} += "/opt/youtubedl-web/static"
FILES_${PN} += "/opt/youtubedl-web/templates/index.html"
FILES_${PN} += "/opt/youtubedl-web/static/style.css"

