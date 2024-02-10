SUMMARY = "MediaServer Web"
SECTION = "network"
LICENSE = "CLOSED"
DEPENDS = "apache2"
RDEPENDS:${PN} += " bash"



SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/MediaServer-Web;branch=main;protocol=https"

S = "${WORKDIR}/git"

do_install() {
	install -d ${D}/usr/htdocs
	install -m 0755 ${S}/*.png ${D}/usr/htdocs
	install -m 0755 ${S}/*.jpg ${D}/usr/htdocs
	install -m 0755 ${S}/*.html ${D}/usr/htdocs
	install -m 0755 ${S}/*.css ${D}/usr/htdocs

	install -d ${D}/usr/htdocs/images
	install -m 0755 ${S}/images/* ${D}/usr/htdocs/images
}

FILES:${PN} += "/usr/htdocs"


