SUMMARY = "MediaServer Web"
SECTION = "network"
LICENSE = "CLOSED"
DEPENDS += "apache2"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/MediaServer-Web;branch=main"

S = "${WORKDIR}/git"

do_install() {
	install -d ${D}/usr/htdocs
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
}

FILES_${PN} += "/usr/htdocs"

