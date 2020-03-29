LICENSE = "GPLv2 & GPLv3"
LIC_FILES_CHKSUM = "file://LICENSE;md5=eb723b61539feef013de476e68b5c50a"
SRCREV = "${PV}"

SRC_URI[md5sum] = "865f4370ad26e3020809a274ad4f123d"
SRC_URI="https://github.com/notandy/ympd/archive/v${PV}.tar.gz \
         file://ympd.service"

DEPENDS = "libmpdclient openssl mpd"

P = "${PN}-${PV}"

S = "${WORKDIR}/${P}"

inherit pkgconfig cmake systemd

BBCLASSEXTEND = "native"
SYSTEMD_PACKAGES = "${PN}"
 

#do_install() {
#    install -d ${D}${bindir}
#    install -m 0755 ympd ${D}${bindir}
#    install -d ${D}${systemd_system_unitdir}
#    install -m 0644 ${WORKDIR}/ympd.service ${D}${systemd_system_unitdir}
#}


