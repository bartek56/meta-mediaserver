LICENSE = "GPLv2 & GPLv3"
LIC_FILES_CHKSUM = "file://LICENSE;md5=eb723b61539feef013de476e68b5c50a"
SRCREV = "${PV}"

SRC_URI[md5sum] = "90206af29c42af66fc900054816aee24"
SRC_URI="https://github.com/notandy/ympd/archive/v${PV}.tar.gz \
         file://ympd.service"

DEPENDS = "libmpdclient openssl mpd"

P = "${PN}-${PV}"

S = "${WORKDIR}/${P}"

inherit pkgconfig cmake systemd

SYSTEMD_PACKAGES = "${PN}" 

do_install_append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_unitdir}/system
}

FILES_${PN}+="/lib/systemd/system/ympd.service"

