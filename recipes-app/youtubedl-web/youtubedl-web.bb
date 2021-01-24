SUMMARY = "Youtubedl-web"
HOMEPAGE = "https://github.com/bartek56/LinuxEmbedded"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "python3 python3-flask metadata-mp3"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/youtubedl-web \
          "
do_install(){
    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.py ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.wsgi ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web/static
    install -m 0644 ${WORKDIR}/git/static/* ${D}/opt/youtubedl-web/static

    install -d ${D}/opt/youtubedl-web/templates
    install -m 0644 ${WORKDIR}/git/templates/* ${D}/opt/youtubedl-web/templates
}


FILES_${PN} += "/opt/youtubedl-web/youtubedl.py"
FILES_${PN} += "/opt/youtubedl-web/youtubedl.wsgi"
FILES_${PN} += "/opt/youtubedl-web/templates"
FILES_${PN} += "/opt/youtubedl-web/static"
FILES_${PN} += "/opt/youtubedl-web/templates/index.html"
FILES_${PN} += "/opt/youtubedl-web/static/style.css"

