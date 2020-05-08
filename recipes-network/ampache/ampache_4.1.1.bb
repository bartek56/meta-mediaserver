DESCRIPTION = "Ampache is a free software Web-based Audio file manager / web Media Server."
HOMEPAGE = "http://www.ampache.org"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://README.md;md5=e3685ab5aa1e420cf67ee242788e4d38"

FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
DEPENDS += " apache2"
RDEPENDS_${PN} += " apache2 mysql5 php php-fpm php-cli php-modphp bash perl"

SRC_URI += "https://github.com/ampache/ampache/releases/download/${PV}/${PN}-${PV}_all.zip \
           file://httpd.conf \
           "

SRC_URI[md5sum] = "eb958442fcc0c6377f9070baa7db13b4"
SRC_URI[sha256sum] = "b8247e3fa551b6bacf0d81959f4ccd91d8f7825cfda34734c8680fdc2391fad1"

S = "${WORKDIR}/${PN}"

inherit systemd

#do_fetch (){ 
#}

do_unpack (){
  unzip ${DL_DIR}/${PN}-${PV}_all.zip -d ${S}/
}

do_install () {
   install -d ${D}/usr/htdocs
 	 cp -r ${S}/ ${D}/usr/htdocs/ampache/

#  install -d ${D}/etc
#  install -m 0644 ${WORKDIR}/php-fpm.conf /etc

#  install -d ${D}/etc/apache2
#  install -m 0644 ${WORKDIR}/httpd.conf /etc/apache2



#  cp ${WORKDIR}/httpd.conf /etc/apache2/httpd.conf  
#  cp ${WORKDIR}/php-fpm.conf /etc/php-fpm.conf

#   install -d ${D}${systemd_system_unitdir}
#   install -m 0644 ${WORKDIR}/ampacheupdate.service ${D}${systemd_system_unitdir}
#   install -m 0644 ${WORKDIR}/ampacheupdate.timer ${D}${systemd_system_unitdir}

#  install -d ${D}${systemd_unitdir}/system

}

FILES_${PN} = "/usr/htdocs/ampache"
#FILES_${PN} += "${systemd_unitdir}/system/*.service"
#FILES_${PN} += "${systemd_unitdir}/system/*.timer"


