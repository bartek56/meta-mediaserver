DESCRIPTION = "systemdlib fo qt5 app"
LICENSE = "LGPL"
HOMEPAGE = "https://github.com/ilpianista/libsystemd-qt"
LIC_FILES_CHKSUM = "file://COPYING;md5=e6a600fd5e1d9cbde2d983680233ad02"

DEPENDS += "qtbase systemd" 
SRC_URI = "git://github.com/bartek56/libsystemd-qt;branch=mediaserver-master;protocol=https"
SRC_URI[sha256sum] = "5bd446d321a12967ea76f7cc63052398c09537ead117a60e12bf72d4942ca9c0"
SRCREV = "${AUTOREV}"

S = "${WORKDIR}/git"

inherit cmake_qt5 pkgconfig

