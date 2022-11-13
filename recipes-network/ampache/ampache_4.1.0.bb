DESCRIPTION = "Ampache is a free software Web-based Audio file manager / web Media Server."
HOMEPAGE = "http://www.ampache.org"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://README.md;md5=8d6af10cff762d9e63ac23aa07429b53"

RDEPENDS:${PN} = "apache2 mysql5 php bash perl"

SRC_URI = "https://github.com/ampache/ampache/releases/download/${PV}/${PN}-${PV}_all.zip"

SRC_URI[md5sum] = "963d35b329d0829f10b391a5913bc926"
SRC_URI[sha256sum] = "4f07f78dbc3bff7ec5e905c655af1073fec00acbdba13062049635d6c9e3883d"

S = "${WORKDIR}/${PN}"

do_unpack (){
  unzip ${DL_DIR}/${PN}-${PV}_all.zip -d ${S}/
}

do_install () {
	install -d ${D}/usr/htdocs/
	cp -r ${S}/ ${D}/usr/htdocs/ampache/
}

FILES:${PN} = "/usr/htdocs/ampache"
