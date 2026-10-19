SUMMARY = "acme"
HOMEPAGE = "https://pypi.org/project/acme/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=03ea1f38aaf7e7cbc333bdf65e6ed51e"
RDEPENDS:${PN} += " python3"
SRC_URI[sha256sum] = "4be4fe6cf3809c3988d75fa1213ce8e784d9d5d8380cac63c2dca555e105653d"
PYPI_PACKAGE = "acme"

inherit pypi setuptools3

