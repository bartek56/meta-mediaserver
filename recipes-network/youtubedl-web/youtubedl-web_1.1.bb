SUMMARY = "Youtubedl-web"
HOMEPAGE = "https://github.com/bartek56/youtubedl-web"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "apache2 python3 python3-flask python3-flask-socketio python3-flask-session metadata-mp3 youtubedl sudo"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/youtubedl-web;branch=master;protocol=https \
           file://www-data \
           file://youtubedl-web.service"

inherit systemd

SYSTEMD_AUTO_ENABLE = "enable"
SYSTEMD_SERVICE:${PN} = "youtubedl-web.service"

do_install(){
    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.py ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.wsgi ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web/static
    install -m 0644 ${WORKDIR}/git/static/* ${D}/opt/youtubedl-web/static

    install -d ${D}/opt/youtubedl-web/Common
    # mail manager is not supported
    rm -f ${WORKDIR}/git/Common/mailManager.py
    install -m 0644 ${WORKDIR}/git/Common/* ${D}/opt/youtubedl-web/Common

    install -d ${D}/opt/youtubedl-web/templates
    install -m 0644 ${WORKDIR}/git/templates/* ${D}/opt/youtubedl-web/templates

    install -d ${D}/etc/sudoers.d
    install -m 0644 ${WORKDIR}/www-data ${D}/etc/sudoers.d

    sed -i 's~mailManager = Mail()~#mailManager is not supported~g' ${D}/opt/youtubedl-web/youtubedl.py
    sed -i 's~from Common.mailManager import Mail~#mailManager is not supported~g' ${D}/opt/youtubedl-web/youtubedl.py

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl-web.service ${D}${systemd_system_unitdir}

#    install -d ${D}/var/log
#    printf "" > ${D}/var/log/youtubedlweb.log
#    chown www-data:www-data /var/log/youtubedlweb.log
}


FILES:${PN} += "/opt/youtubedl-web/*"
FILES:${PN} += "/var/log/youtubedlweb.log"
