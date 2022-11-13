LICENSE = "GPLv2 & GPLv3"
LIC_FILES_CHKSUM = "file://LICENSE;md5=eb723b61539feef013de476e68b5c50a"
SRCREV = "${PV}"

SRC_URI[md5sum] = "90206af29c42af66fc900054816aee24"
SRC_URI="https://github.com/notandy/ympd/archive/v${PV}.tar.gz \
         file://ympd.service \
         file://001-resolve_mpd_duplicate_during_linking.patch"

DEPENDS = "libmpdclient openssl mpd"

P = "${PN}-${PV}"
S = "${WORKDIR}/${P}"

inherit pkgconfig cmake systemd

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE_${PN} = "${PN}.service"

do_compile:prepend() {
    find ${S} -name CMakeLists.txt | xargs sed -i 's/set(CMAKE_C_FLAGS "-std=gnu99 -Wall")/set(CMAKE_C_FLAGS ${CMAKE_C_FLAGS})/g'
}

do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/ympd.service ${D}${systemd_system_unitdir}
}

FILES:${PN} += "${systemd_system_unitdir}/ympd.service"

