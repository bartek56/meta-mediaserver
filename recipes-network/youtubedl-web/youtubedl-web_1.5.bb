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

S = "${UNPACKDIR}/youtubedl-web-${PV}"

SYSTEMD_AUTO_ENABLE = "enable"
SYSTEMD_SERVICE:${PN} = "youtubedl-web.service"

do_install(){
    install -d ${D}/opt/youtubedl-web
    install -m 0644 ${S}/youtubedlWeb/youtubedl.py ${D}/opt/youtubedl-web
    install -m 0775 ${S}/youtubedlWeb/install_bootstrap.sh ${D}/opt/youtubedl-web
    install -m 0644 ${S}/youtubedl.wsgi ${D}/opt/youtubedl-web

    install -d ${D}/opt/youtubedl-web/youtubedlWeb

    install -m 0644 ${S}/youtubedlWeb/config.py ${D}/opt/youtubedl-web/youtubedlWeb
    install -m 0644 ${S}/youtubedlWeb/__init__.py ${D}/opt/youtubedl-web/youtubedlWeb

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/routes
    install -m 0644 ${S}/youtubedlWeb/routes/* ${D}/opt/youtubedl-web/youtubedlWeb/routes

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/static
    install -m 0644 ${S}/youtubedlWeb/static/* ${D}/opt/youtubedl-web/youtubedlWeb/static

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/Common
    cp -r ${S}/youtubedlWeb/Common/* ${D}/opt/youtubedl-web/youtubedlWeb/Common

    install -d ${D}/opt/youtubedl-web/youtubedlWeb/templates
    install -m 0644 ${S}/youtubedlWeb/templates/* ${D}/opt/youtubedl-web/youtubedlWeb/templates

    install -d ${D}/etc/sudoers.d
    install -m 0644 ${UNPACKDIR}/www-data ${D}/etc/sudoers.d

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/youtubedl-web.service ${D}${systemd_system_unitdir}

    install -d ${D}/etc/apache2/conf.d
    install -m 0755 ${UNPACKDIR}/youtubedl-web.conf ${D}/etc/apache2/conf.d

#    install -d ${D}/var/log
#    printf "" > ${D}/var/log/youtubedlweb.log
#    chown www-data:www-data /var/log/youtubedlweb.log
}


FILES:${PN} += "/opt/youtubedl-web/*"
FILES:${PN} += "/var/log/youtubedlweb.log"
FILES:${PN} += "/etc/apache2/conf.d/youtubedl.conf"
