SUMMARY = "MediaServer GUI app"
SECTION = "examples"
LICENSE = "GPLv2"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=d32239bcb673463ab874e80d47fae504"

DEPENDS = "qtbase qtsvg qtmultimedia qtxmlpatterns ruby-native"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/soramimi/SkyMPC \
          file://skyMPC-yocto.patch \
          "

S = "${WORKDIR}/git"

require recipes-qt/qt5/qt5.inc

inherit qmake5 

FILES_${PN} += "/opt/SkyMPC"

