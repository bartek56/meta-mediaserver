DESCRIPTION = "Ampache is a free software Web-based Audio file manager / web Media Server."
HOMEPAGE = "http://www.ampache.org"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://README.md;md5=e3685ab5aa1e420cf67ee242788e4d38"

RDEPENDS_${PN} = "apache2 mysql5 php bash perl"

SRC_URI = "https://github.com/ampache/ampache/releases/download/${PV}/${PN}-${PV}_all.zip"

SRC_URI[md5sum] = "eb958442fcc0c6377f9070baa7db13b4"
SRC_URI[sha256sum] = "b8247e3fa551b6bacf0d81959f4ccd91d8f7825cfda34734c8680fdc2391fad1"

S = "${WORKDIR}/${PN}"

do_unpack (){
  unzip ${DL_DIR}/${PN}-${PV}_all.zip -d ${S}/
}

do_install () {
	install -d ${D}/usr/htdocs/
	cp -r ${S}/ ${D}/usr/htdocs/ampache/
}

FILES_${PN} = "/usr/htdocs/ampache"


