SUMMARY = "MediaServer Qt6 startup GUI app"
SECTION = "apps"
LICENSE = "CLOSED"
DEPENDS += "qtbase qtdeclarative qtdeclarative-native"
RDEPENDS:${PN} = "qtbase qtdeclarative qtdeclarative-qmlplugins qtvirtualkeyboard"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/MediaServer;branch=qt6;protocol=https \
          file://startup.service \
          file://0001-cmake-make-unit-tests-optional.patch \
"

inherit qt6-cmake systemd

EXTRA_OECMAKE += "-DBUILD_TESTING=OFF"

SYSTEMD_AUTO_ENABLE:${PN} = "enable"
SYSTEMD_SERVICE:${PN} = "startup.service"

do_compile() {
    cmake_runcmake_build --target MediaServerStartup
}

do_install() {
    install -d ${D}/opt
    install -m 0755 ${B}/MediaServerStartup/MediaServerStartup ${D}/opt/MediaServerStartup

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/startup.service ${D}${systemd_system_unitdir}
}

FILES:${PN} += " \
    /opt/MediaServerStartup \
    ${systemd_system_unitdir}/startup.service \
"
