SUMMARY = "libetrv for contol Danfoss Eco Bluetooth LE thermostat"
HOMEPAGE = "https://github.com/AdamStrojek/libetrv"
LICENSE = "Apache"
LIC_FILES_CHKSUM = "file://LICENSE;md5=86d3f3a95c324c9479bd8986968f4327"

PYPI_SRC_URI = "https://github.com/AdamStrojek/libetrv/archive/refs/tags/v${PV}.tar.gz"
RDEPENDS:${PN} = " python3-fire bluepy python3-xxtea python3-loguru python3-cstruct python3-pytest"

SRC_URI[sha256sum] = "8bdfe2527db648396eb20a85940a13a4fb87c814b2f1307dfea7ac1dfa4fb02f"
PYPI_PACKAGE = "libetrv"

inherit pypi setuptools3

do_configure:prepend() {
    find ${WORKDIR}/libetrv-${PV} -name setup.py | xargs sed -i 's~from distutils.core import setup~from setuptools import setup~g'
}
