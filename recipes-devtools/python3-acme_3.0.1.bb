SUMMARY = "acme"
HOMEPAGE = "https://pypi.org/project/acme/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=03ea1f38aaf7e7cbc333bdf65e6ed51e"
RDEPENDS:${PN} += " python3"
SRC_URI[sha256sum] = "2f4ae207c8a6791a2bc74cd18d60274766f483c2059145b0142cbb43e761331c"
PYPI_PACKAGE = "acme"

inherit pypi setuptools3

