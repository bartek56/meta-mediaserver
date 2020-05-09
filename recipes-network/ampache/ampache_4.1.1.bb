DESCRIPTION = "Ampache is a free software Web-based Audio file manager / web Media Server."
HOMEPAGE = "http://www.ampache.org"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://README.md;md5=e3685ab5aa1e420cf67ee242788e4d38"

FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
DEPENDS += " apache2"
RDEPENDS_${PN} += " apache2 mysql5 php php-fpm php-cli php-modphp bash perl"

SRC_URI += "https://github.com/ampache/ampache/releases/download/${PV}/${PN}-${PV}_all.zip \
           file://httpd.conf \
           file://ampacheupdate.service \
           file://ampacheupdate.timer \
           file://php-fpm.conf \
           "

SRC_URI[md5sum] = "eb958442fcc0c6377f9070baa7db13b4"
SRC_URI[sha256sum] = "b8247e3fa551b6bacf0d81959f4ccd91d8f7825cfda34734c8680fdc2391fad1"

S = "${WORKDIR}/${PN}"

inherit systemd

#do_fetch (){ 
#}

do_unpack (){
  unzip ${DL_DIR}/${PN}-${PV}_all.zip -d ${S}/
  cp ${THISDIR}/${PN}/php-fpm.conf ${WORKDIR}/
  cp ${THISDIR}/${PN}/httpd.conf ${WORKDIR}/
  cp ${THISDIR}/${PN}/ampacheupdate.service ${WORKDIR}/
  cp ${THISDIR}/${PN}/ampacheupdate.timer ${WORKDIR}/
}

do_install () {
   install -d ${D}/usr/htdocs
 	 cp -r ${S}/ ${D}/usr/htdocs/ampache/

   install -d ${D}/etc
   install -m 0644 ${WORKDIR}/php-fpm.conf ${D}/etc

   install -d ${D}/etc/apache2
   install -m 0644 ${WORKDIR}/httpd.conf ${D}/etc/apache2


   install -d ${D}${systemd_system_unitdir}
   cp ${WORKDIR}/ampacheupdate.service ${D}${systemd_system_unitdir}
   cp ${WORKDIR}/ampacheupdate.timer ${D}${systemd_system_unitdir}

}

FILES_${PN} += "/usr/htdocs/ampache"
FILES_${PN} += "${systemd_system_unitdir}/ampacheupdate.service"
FILES_${PN} += "${systemd_system_unitdir}/ampacheupdate.timer"
FILES_${PN} += "/etc/apache2/httpd.conf"
FILES_${PN} += "/etc/php-fpm.conf"


