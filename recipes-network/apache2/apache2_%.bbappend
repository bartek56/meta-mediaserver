SUMMARY = "Apache config"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://httpd.conf \
            file://youtubedl-web.conf \
            file://apache2.service \           
"

do_install:append () {
	install -d ${D}/etc/apache2
	install -m 0755 ${WORKDIR}/httpd.conf ${D}/etc/apache2
	install -m 0755 ${WORKDIR}/youtubedl-web.conf ${D}/etc/apache2/conf.d
}

FILES:${PN} += "/etc/apache2/httpd.conf"
FILES:${PN} += "/etc/apache2/conf.d/youtubedl.conf"

