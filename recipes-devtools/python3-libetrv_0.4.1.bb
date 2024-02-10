SUMMARY = "libetrv for contol Danfoss Eco Bluetooth LE thermostat"
HOMEPAGE = "https://github.com/AdamStrojek/libetrv"
LICENSE = "Apache"
LIC_FILES_CHKSUM = "file://LICENSE;md5=86d3f3a95c324c9479bd8986968f4327"

PYPI_SRC_URI = "git://github.com/bartek56/libetrv;protocol=https;branch=master"
SRCREV = "77a4409657efc66a06667fb0400ef6b0c0b97ab1"

RDEPENDS:${PN} = " python3-fire bluepy python3-xxtea python3-loguru python3-cstruct python3-pytest"

SRC_URI[sha256sum] = "8bdfe2527db648396eb20a85940a13a4fb87c814b2f1307dfea7ac1dfa4fb02f"
PYPI_PACKAGE = "libetrv"

inherit pypi setuptools3

S = "${WORKDIR}/git"
