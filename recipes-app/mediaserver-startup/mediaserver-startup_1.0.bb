SUMMARY = "MediaServer startup GUI app"
SECTION = "apps"
LICENSE = "CLOSED"
DEPENDS += "qtbase qtdeclarative qtquickcontrols2 systemdlib-qt" 
RDEPENDS_${PN} = "qtbase qtquickcontrols2 qtvirtualkeyboard systemdlib-qt qtdeclarative"
SRC_URI[md5sum] = "5900b09d36848e446e53e19c413ec363"
SRC_URI[sha256sum] = "b828614be6b8be36493e18b7c239d6264dd78e1f4e325301f2d1722cad6eaf5e"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/MediaServer;protocol=https \
          file://startup.service "


S = "${WORKDIR}/git"

require recipes-qt/qt5/qt5.inc

inherit qmake5 systemd

SYSTEMD_AUTO_ENABLE = "enable" 
SYSTEMD_SERVICE_${PN} = "startup.service"

do_compile() {
    oe_runmake sub-MediaServerStartup 
}

do_install() {
    oe_runmake sub-MediaServerStartup-install_subtargets INSTALL_ROOT=${D}
}

do_install_append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/startup.service ${D}${systemd_unitdir}/system
}

FILES_${PN} += "/opt/MediaServerStartup"
FILES_${PN} += "${systemd_system_unitdir}/startup.service"

