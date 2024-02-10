SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

DEPENDS:append_class-target = " curl"
EXTRA_OECONF:append_class-target = " --with-curl=${STAGING_LIBDIR}/.."

DEPENDS:append_class-target = " gd libwebp jpeg libpng libxpm"
EXTRA_OECONF:append_class-target = " --enable-gd  --with-webp --with-jpeg --with-xpm --with-freetype "

PACKAGECONFIG = "mysql sqlite3 imap opcache openssl zip apache2 \
                 ${@bb.utils.filter('DISTRO_FEATURES', 'ipv6 pam', d)} \
                 "

do_install:append () {
	install -d ${D}/etc
}

