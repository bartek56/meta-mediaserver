DESCRIPTION = "Ampache is a free software Web-based Audio file manager / web Media Server."
HOMEPAGE = "http://www.ampache.org"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://README.md;md5=e3685ab5aa1e420cf67ee242788e4d38"

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
DEPENDS += " apache2"
RDEPENDS:${PN} += " apache2 mod-wsgi mysql5 php php-fpm php-cli php-modphp bash perl"

SRC_URI += "https://github.com/ampache/ampache/releases/download/${PV}/${PN}-${PV}_all.zip \
           file://ampacheupdate.service \
           file://ampacheupdate.timer \
           "

SRC_URI[md5sum] = "eb958442fcc0c6377f9070baa7db13b4"
SRC_URI[sha256sum] = "b8247e3fa551b6bacf0d81959f4ccd91d8f7825cfda34734c8680fdc2391fad1"

S = "${WORKDIR}/${PN}"

inherit systemd

do_unpack (){
  unzip ${DL_DIR}/${PN}-${PV}_all.zip -d ${S}/
  cp ${THISDIR}/${PN}/ampacheupdate.service ${WORKDIR}/
  cp ${THISDIR}/${PN}/ampacheupdate.timer ${WORKDIR}/
}

do_install () {
    install -d ${D}/usr/htdocs
    cp -r ${S}/ ${D}/usr/htdocs/ampache/

    install -d ${D}${systemd_system_unitdir}
    cp ${WORKDIR}/ampacheupdate.service ${D}${systemd_system_unitdir}
    cp ${WORKDIR}/ampacheupdate.timer ${D}${systemd_system_unitdir}

    chmod -R 777 ${D}/usr/htdocs/ampache/config
	cp ${D}/usr/htdocs/ampache/channel/.htaccess.dist ${D}/usr/htdocs/ampache/channel/.htaccess
    chmod 777 ${D}/usr/htdocs/ampache/channel/.htaccess
	cp ${D}/usr/htdocs/ampache/rest/.htaccess.dist ${D}/usr/htdocs/ampache/rest/.htaccess
    chmod 777 ${D}/usr/htdocs/ampache/rest/.htaccess
	cp ${D}/usr/htdocs/ampache/play/.htaccess.dist ${D}/usr/htdocs/ampache/play/.htaccess
    chmod 777 ${D}/usr/htdocs/ampache/play/.htaccess
}

FILES:${PN} += "/usr/htdocs/ampache"
FILES:${PN} += "${systemd_system_unitdir}/ampacheupdate.service"
FILES:${PN} += "${systemd_system_unitdir}/ampacheupdate.timer"
