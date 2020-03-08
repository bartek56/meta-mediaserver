SUMMARY = "Simple Qt5 Quick application"
SECTION = "examples"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"
#LIC_FILES_CHKSUM = "file:// URL. SRCREV"
DEPENDS += "qtbase qtdeclarative qtquickcontrols2"

SRC_URI[md5sum] = "5900b09d36848e446e53e19c413ec363"
SRC_URI[sha256sum] = "b828614be6b8be36493e18b7c239d6264dd78e1f4e325301f2d1722cad6eaf5e"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/MediaServer"

S = "${WORKDIR}/git"

require recipes-qt/qt5/qt5.inc

do_install() {
      install -d ${D}${bindir}
      install -m 0755 MediaServerApp/MediaServerApp ${D}${bindir}
}

inherit qmake5
