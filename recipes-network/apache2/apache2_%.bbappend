SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://httpd.conf \
            file://youtubedl-web.conf \
            file://ampache.png \
            file://background.jpg \
            file://dlna.png \
            file://filebrowser.png \
            file://ftp.png \
            file://index.php \
            file://samba.png \
            file://style.css \
            file://transmission.png \
            file://tvheadend.png \
            file://ympd.svg \
            file://jellyfin.png \
            file://alarm.png \
"

do_install_append () {
	install -d ${D}/etc/apache2
	install -m 0755 ${WORKDIR}/httpd.conf ${D}/etc/apache2
	install -m 0755 ${WORKDIR}/youtubedl-web.conf ${D}/etc/apache2/conf.d

	install -d ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/ampache.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/background.jpg ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/dlna.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/filebrowser.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/ftp.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/index.php ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/samba.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/style.css ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/transmission.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/tvheadend.png ${D}/usr/htdocs
	install -m 0755 ${WORKDIR}/ympd.svg ${D}/usr/htdocs
    install -m 0755 ${WORKDIR}/jellyfin.png ${D}/usr/htdocs
    install -m 0755 ${WORKDIR}/alarm.png ${D}/usr/htdocs
}

FILES_${PN} += "/etc/apache2/httpd.conf"
FILES_${PN} += "/usr/htdocs/ampache.png"
FILES_${PN} += "/usr/htdocs/background.jpg"
FILES_${PN} += "/usr/htdocs/dlna.png"
FILES_${PN} += "/usr/htdocs/filebrowser.png"
FILES_${PN} += "/usr/htdocs/ftp.png"
FILES_${PN} += "/usr/htdocs/index.php"
FILES_${PN} += "/usr/htdocs/samba.png"
FILES_${PN} += "/usr/htdocs/style.css"
FILES_${PN} += "/usr/htdocs/transmission.png"
FILES_${PN} += "/usr/htdocs/tvheadend.png"
FILES_${PN} += "/usr/htdocs/ympd.svg"
FILES_${PN} += "/usr/htdocs/jellyfin.png"
FILES_${PN} += "/usr/htdocs/alarm.png"

