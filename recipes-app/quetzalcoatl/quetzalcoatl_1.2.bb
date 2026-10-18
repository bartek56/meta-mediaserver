SUMMARY = "MPD client Qt6"
SECTION = "apps"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=b34f40e0535e51cae4b93caa4dbd99bf"

DEPENDS += "qtbase libmpdclient"
RDEPENDS:${PN} += "qtbase libmpdclient bash"
PRIVATE_LIBS:${PN} = "libcontroller.so"
FILES:${PN}-dev:remove = "${libdir}/lib*.so"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/quetzalcoatl;branch=mediaserverQt6;protocol=https \
           file://mpc_mediaserver.service \
"

inherit qt6-cmake pkgconfig systemd

do_install() {
    install -d ${D}/opt
    install -m 0755 ${B}/quetzalcoatl ${D}/opt
    install -d ${D}${libdir}
    install -d ${D}${datadir}/icons
    cp -r ${S}/app/icons/breeze ${D}${datadir}/icons/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/mpc_mediaserver.service ${D}${systemd_system_unitdir}
}

SYSTEMD_AUTO_ENABLE:${PN} = "enable"
SYSTEMD_SERVICE:${PN} = "mpc_mediaserver.service"

FILES:${PN} += " \
    /opt/quetzalcoatl \
    ${datadir}/icons/breeze/* \
    ${systemd_system_unitdir}/mpc_mediaserver.service \
"
