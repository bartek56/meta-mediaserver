SUMMARY = "Apache config"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://youtubedl-web.conf \
            file://apache2.service \           
"

do_install:append () {
	install -d ${D}/etc/apache2
	install -m 0755 ${WORKDIR}/youtubedl-web.conf ${D}/etc/apache2/conf.d
	sed -i 's~DocumentRoot "/usr/share/apache2/default-site/htdocs"~DocumentRoot "/usr/htdocs"~g' ${D}/${sysconfdir}/${BPN}/httpd.conf	
	sed -i 's~<Directory "/usr/share/apache2/default-site/htdocs"~<Directory "/usr/htdocs"~g' ${D}/${sysconfdir}/${BPN}/httpd.conf	
}

FILES:${PN} += "/etc/apache2/conf.d/youtubedl.conf"
