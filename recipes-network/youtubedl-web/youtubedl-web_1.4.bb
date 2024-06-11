SUMMARY = "Youtubedl-web"
HOMEPAGE = "https://github.com/bartek56/youtubedl-web"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "bash apache2 python3 python3-flask python3-flask-socketio python3-flask-session metadata-mp3 (= ${PV}) youtubedl sudo"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/youtubedl-web;branch=master;protocol=https \
           file://www-data \
           file://youtubedl-web.conf \
           file://youtubedl-web.service"

inherit systemd

SYSTEMD_AUTO_ENABLE = "enable"
SYSTEMD_SERVICE:${PN} = "youtubedl-web.service"

do_install(){
    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/youtubedl.py ${D}/opt/youtubedl-web
    install -m 0775 ${WORKDIR}/git/youtubedlWeb/install_bootstrap.sh ${D}/opt/youtubedl-web
    install -m 0644 ${WORKDIR}/git/youtubedl.wsgi ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web/youtubedlWeb

    install -m 0644 ${WORKDIR}/git/youtubedlWeb/config.py ${D}/opt/youtubedl-web/youtubedlWeb
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/__init__.py ${D}/opt/youtubedl-web/youtubedlWeb

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/routes
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/routes/* ${D}/opt/youtubedl-web/youtubedlWeb/routes

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/static
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/static/* ${D}/opt/youtubedl-web/youtubedlWeb/static

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/Common
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/Common/* ${D}/opt/youtubedl-web/youtubedlWeb/Common

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/templates
    install -m 0644 ${WORKDIR}/git/youtubedlWeb/templates/* ${D}/opt/youtubedl-web/youtubedlWeb/templates

    install -d ${D}/etc/sudoers.d
    install -m 0644 ${WORKDIR}/www-data ${D}/etc/sudoers.d

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/youtubedl-web.service ${D}${systemd_system_unitdir}
    
    install -d ${D}/etc/apache2/conf.d
    install -m 0755 ${WORKDIR}/youtubedl-web.conf ${D}/etc/apache2/conf.d

#    install -d ${D}/var/log
#    printf "" > ${D}/var/log/youtubedlweb.log
#    chown www-data:www-data /var/log/youtubedlweb.log
}


FILES:${PN} += "/opt/youtubedl-web/*"
FILES:${PN} += "/var/log/youtubedlweb.log"
FILES:${PN} += "/etc/apache2/conf.d/youtubedl.conf"
