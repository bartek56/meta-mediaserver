LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=eb723b61539feef013de476e68b5c50a"
SRCREV = "ec008a4995666d673bd4cb3926fae7f4b6aa3239"

SRC_URI = "git://github.com/notandy/ympd.git;branch=master;protocol=https \
         file://ympd.service \
         file://001-resolve_mpd_duplicate_during_linking.patch \
         file://0002-update-cmake-minimum-version.patch"

DEPENDS = "libmpdclient openssl mpd"

inherit pkgconfig cmake systemd

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE:${PN} = "${PN}.service"

do_compile:prepend() {
    find ${S} -name CMakeLists.txt | xargs sed -i 's/set(CMAKE_C_FLAGS "-std=gnu99 -Wall")/set(CMAKE_C_FLAGS ${CMAKE_C_FLAGS})/g'
}

do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/ympd.service ${D}${systemd_system_unitdir}
}

FILES:${PN} += "${systemd_system_unitdir}/ympd.service"
