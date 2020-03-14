LICENSE = "GPLv2 & GPLv3"
LIC_FILES_CHKSUM = "file://COPYING;md5=0dd9fcdc1416ff123c41c785192a1895"

SRCREV = "${PV}"

SRC_URI[md5sum] = "a1b8113ebc3402787312ecb443d9d3c1"
DEPENDS = "libevent gnutls openssl libtool intltool-native curl glib-2.0-native"

P = "${PN}-${PV}"
SRC_URI = "https://github.com/transmission/transmission-releases/raw/master/${P}.tar.xz"

S = "${WORKDIR}/${P}"
EXTRA_OECONF="--enable-cli"
inherit autotools gettext

B = "${S}"

do_configure_prepend() {
	sed -i /AM_GLIB_GNU_GETTEXT/d ${S}/configure.ac
	cd ${S}
	./update-version-h.sh
	intltoolize --copy --force --automake
}


#inherit pkgconfig cmake
#inherit autotools

#PACKAGECONFIG[gtk] = " --with-gtk,--without-gtk,gtk+3,"
#PACKAGECONFIG[systemd] = "--with-systemd-daemon,--without-systemd-daemon,systemd,"



