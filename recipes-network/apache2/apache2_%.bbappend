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
	sed -i 's~User daemon~User www-data~g' ${D}/${sysconfdir}/${BPN}/httpd.conf
	sed -i 's~Group daemon~Group www-data~g' ${D}/${sysconfdir}/${BPN}/httpd.conf

	sed -i 's~#LoadModule proxy_wstunnel_module /usr/libexec/apache2/modules/mod_proxy_wstunnel.so~LoadModule proxy_wstunnel_module /usr/libexec/apache2/modules/mod_proxy_wstunnel.so~g' ${D}/${sysconfdir}/${BPN}/httpd.conf
	sed -i 's~#LoadModule proxy_module /usr/libexec/apache2/modules/mod_proxy.so~LoadModule proxy_module /usr/libexec/apache2/modules/mod_proxy.so~g' ${D}/${sysconfdir}/${BPN}/httpd.conf
	sed -i 's~#LoadModule proxy_http_module /usr/libexec/apache2/modules/mod_proxy_http.so~LoadModule proxy_http_module /usr/libexec/apache2/modules/mod_proxy_http.so~g' ${D}/${sysconfdir}/${BPN}/httpd.conf
}

FILES:${PN} += "/etc/apache2/conf.d/youtubedl.conf"
