SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://php-fpm.conf"

do_install_append () {
	install -d ${D}/etc
	install -m 0755 ${WORKDIR}/php-fpm.conf ${D}/etc
}

FILES_${PN} += "/etc/php-fpm.conf"


