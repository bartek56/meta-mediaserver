LICENSE = "GPLv2 & GPLv3"
LIC_FILES_CHKSUM = "file://COPYING;md5=0dd9fcdc1416ff123c41c785192a1895"

SRCREV = "${PV}"

SRC_URI[md5sum] = "a1b8113ebc3402787312ecb443d9d3c1"
DEPENDS = "libevent gnutls openssl libtool intltool-native curl glib-2.0-native"

P = "${PN}-${PV}"
SRC_URI = "https://github.com/transmission/transmission-releases/raw/master/${P}.tar.xz \
           file://transmission-daemon.service \
           file://settings.json \
"

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

do_install_append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/transmission-daemon.service ${D}${systemd_system_unitdir}
        
        install -D ${D}/etc/transmission-daemon
        install -m 0644 ${WORKDIR}/settings.json ${D}/etc/transmission-daemon
}

FILES_${PN} += "/lib/systemd/system/transmission-daemon.service"
FILES_${PN} += "/etc/transmission-daemon/settings.json"


