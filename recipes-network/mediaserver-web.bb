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
	install -m 0755 ${S}/install_bootstrap.sh ${D}/usr/htdocs
	install -m 0755 ${S}/ampache.png ${D}/usr/htdocs
	install -m 0755 ${S}/background.jpg ${D}/usr/htdocs
	install -m 0755 ${S}/youtubedl.png ${D}/usr/htdocs
	install -m 0755 ${S}/dlna.png ${D}/usr/htdocs
	install -m 0755 ${S}/filebrowser.png ${D}/usr/htdocs
	install -m 0755 ${S}/ftp.png ${D}/usr/htdocs
	install -m 0755 ${S}/index.html ${D}/usr/htdocs
	install -m 0755 ${S}/samba.png ${D}/usr/htdocs
	install -m 0755 ${S}/style.css ${D}/usr/htdocs
	install -m 0755 ${S}/transmission.png ${D}/usr/htdocs
	install -m 0755 ${S}/tvheadend.png ${D}/usr/htdocs
	install -m 0755 ${S}/ympd.svg ${D}/usr/htdocs
    install -m 0755 ${S}/jellyfin.png ${D}/usr/htdocs
    install -m 0755 ${S}/alarm.png ${D}/usr/htdocs

	install -d ${D}/usr/htdocs/images
	install -m 0755 ${S}/images/IMG_20210611_210755.jpg ${D}/usr/htdocs/images
	install -m 0755 ${S}/images/IMG_20210722_105646.jpg ${D}/usr/htdocs/images
	install -m 0755 ${S}/images/IMG_20210722_150715.jpg ${D}/usr/htdocs/images
}

FILES:${PN} += "/usr/htdocs"


