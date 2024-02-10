DESCRIPTION = "Transmission is a fast, easy, and free BitTorrent client"
SECTION = "network"
HOMEPAGE = "https://transmissionbt.com/"
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://COPYING;md5=ba8199e739948e198310093de27175fa"

DEPENDS = "curl libevent gnutls openssl libtool intltool-native glib-2.0-native"
RDEPENDS:${PN}-web = "${PN}"

SRC_URI = " \
	gitsm://github.com/transmission/transmission;branch=main;protocol=https \
    file://settings.json \
    file://transmission-daemon.service \
"

SRCREV = "2a57b17031053999e66c7c094e5d6cd6ec4666aa"
PV = "4.0.2"

inherit cmake pkgconfig systemd

S = "${WORKDIR}/git"


SYSTEMD_SERVICE:${PN} = "transmission-daemon.service"

do_install:append() {
    install -d ${D}/etc/transmission-daemon
    install -m 0644 ${WORKDIR}/settings.json ${D}/etc/transmission-daemon
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/transmission-daemon.service ${D}${systemd_unitdir}/system
}

FILES:${PN} = "${bindir}/transmission-daemon /usr/bin/transmission-create /usr/bin/transmission-show /usr/bin/transmission-edit /usr/bin/transmission-remote"
FILES:${PN} += "/etc/transmission-daemon/settings.json"
FILES:${PN} += "/usr/share/transmission"

