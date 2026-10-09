SUMMARY = "Snapcast"
DESCRIPTION = "Snapcast is a multiroom client-server audio player"
LICENSE = "GPL-3.0-only"


SRC_URI = " \
    git://github.com/snapcast/snapcast.git;protocol=https;branch=develop \
    file://snapclient.service \
    file://snapserver.service \
    file://snapserver.conf \
    file://snapclient.conf \
"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7702f203b58979ebbc31bfaeb44f219c"

SRCREV = "f12373479243e93a97237592d6a3703539ec41d5"

DEPENDS += " \
    avahi \
    boost \
    alsa-lib \
    flac \
    libvorbis \
    libopus \
    pulseaudio \
"

inherit cmake systemd pkgconfig

EXTRA_OECMAKE = "-DBUILD_TESTS=OFF -DBUILD_STATIC_LIBS=OFF"

RDEPENDS:${PN}-client += "pulseaudio"

PACKAGES = " \
    ${PN}-client \
    ${PN}-server \
    ${PN}-dbg \
    ${PN}-client-doc \
    ${PN}-server-doc \
"


do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/snapclient.service ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/snapserver.service ${D}${systemd_system_unitdir}

    install -d ${D}${sysconfdir}
    install -m 0644 ${UNPACKDIR}/snapserver.conf ${D}${sysconfdir}/
    install -m 0644 ${UNPACKDIR}/snapclient.conf ${D}${sysconfdir}/

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
