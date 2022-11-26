SUMMARY = "Youtubedl-web"
HOMEPAGE = "https://github.com/bartek56/youtubedl-web"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "apache2 python3 python3-flask metadata-mp3 youtubedl sudo"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/youtubedl-web;branch=master;protocol=https \
           file://www-data"

do_install(){
    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.py ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.wsgi ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web/static
    install -m 0644 ${WORKDIR}/git/static/* ${D}/opt/youtubedl-web/static

    install -d ${D}/opt/youtubedl-web/templates
    install -m 0644 ${WORKDIR}/git/templates/* ${D}/opt/youtubedl-web/templates

    install -d ${D}/etc/sudoers.d
    install -m 0644 ${WORKDIR}/www-data ${D}/etc/sudoers.d

#    install -d ${D}/var/log
#    printf "" > ${D}/var/log/youtubedlweb.log
#    chown www-data:www-data /var/log/youtubedlweb.log
}


FILES:${PN} += "/opt/youtubedl-web/youtubedl.py"
FILES:${PN} += "/opt/youtubedl-web/youtubedl.wsgi"
FILES:${PN} += "/opt/youtubedl-web/templates"
FILES:${PN} += "/opt/youtubedl-web/static"
FILES:${PN} += "/opt/youtubedl-web/templates/index.html"
FILES:${PN} += "/opt/youtubedl-web/static/style.css"
FILES:${PN} += "/var/log/youtubedlweb.log"

