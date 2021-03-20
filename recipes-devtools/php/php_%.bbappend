SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://php-fpm.conf"

DEPENDS_append_class-target = " curl"
EXTRA_OECONF_append_class-target = " --with-curl=${STAGING_LIBDIR}/.."

DEPENDS_append_class-target = " gd libwebp jpeg libpng libxpm"
EXTRA_OECONF_append_class-target = " --with-gd=${STAGING_LIBDIR}/..  --with-webp-dir=${STAGING_LIBDIR}/.. --with-png-dir=${STAGING_LIBDIR}/.. --with-jpeg-dir=${STAGING_LIBDIR}/.. --with-xpm-dir=${STAGING_LIBDIR}/.. --with-freetype-dir=${STAGING_LIBDIR}/.."

PACKAGECONFIG = "mysql sqlite3 imap opcache openssl ipv6 pam zip apache2"



do_install_append () {
	install -d ${D}/etc
	install -m 0755 ${WORKDIR}/php-fpm.conf ${D}/etc
}

FILES_${PN} += "/etc/php-fpm.conf"


