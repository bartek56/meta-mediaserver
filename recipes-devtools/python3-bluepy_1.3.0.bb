SUMMARY = "bluepy"
HOMEPAGE = "https://pypi.org/project/bluepy/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README;md5=0e50fa260baaf98bc02337980811786a"

DEPENDS += " glib-2.0"
RDEPENDS_${PN} += "bluez5"

TARGET_CC_ARCH += "${LDFLAGS}"

SRC_URI[sha256sum] = "2a71edafe103565fb990256ff3624c1653036a837dfc90e1e32b839f83971cec"
PYPI_PACKAGE = "bluepy"

inherit pypi setuptools3 python3-dir

