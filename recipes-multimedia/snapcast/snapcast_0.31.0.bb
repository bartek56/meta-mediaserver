SUMMARY = "Snpcast"
DESCRIPTION = "Snapcast is a multiroom client-server audio player"
LICENSE = "GPLv3"


SRC_URI = " \
    git://github.com/badaix/snapcast.git;protocol=https;branch=master \
    file://snapclient.service \
    file://snapserver.service \
    file://snapserver.conf \
    file://snapclient.conf \
"
LIC_FILES_CHKSUM = "file://../git/LICENSE;md5=7702f203b58979ebbc31bfaeb44f219c"

SRCREV = "9c9ebaead8b1a5f7db9ff834f5c5692b8eb4ee43"

DEPENDS += " \
    avahi \
    boost \
    alsa-lib \
    flac \
    libvorbis \
"

inherit cmake systemd pkgconfig

EXTRA_OECMAKE = "-DBUILD_TESTS=OFF -DBUILD_STATIC_LIBS=OFF"

PACKAGES = " \
    ${PN}-client \
    ${PN}-server \
    ${PN}-dbg \
    ${PN}-client-doc \
    ${PN}-server-doc \
"

S = "${WORKDIR}/git"

do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/snapclient.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/snapserver.service ${D}${systemd_system_unitdir}

    install -d ${D}${sysconfdir}
    install -m 0644 ${WORKDIR}/snapserver.conf ${D}${sysconfdir}/
    install -m 0644 ${WORKDIR}/snapclient.conf ${D}${sysconfdir}/

    # Remove unneeded icons
    rm -rf ${D}${datadir}/pixmaps
}

SYSTEMD_PACKAGES = "${PN}-client ${PN}-server"
SYSTEMD_SERVICE_${PN}-client = "snapclient.service"
SYSTEMD_SERVICE_${PN}-server = "snapserver.service"

FILES:${PN}-client = " \
    ${bindir}/snapclient \
    ${sysconfdir}/snapclient.conf \
    ${systemd_system_unitdir}/snapclient.service \
"

FILES:${PN}-client-doc = "${mandir}/man1/snapclient*"

FILES:${PN}-server = " \
    ${bindir}/snapserver \
    ${sysconfdir}/snapserver.conf \
    ${sysconfdir}/snapserver/certs \
    ${datadir}/snapserver/* \
    ${systemd_system_unitdir}/snapserver.service \
"

FILES:${PN}-server-doc = "${mandir}/man1/snapserver*"