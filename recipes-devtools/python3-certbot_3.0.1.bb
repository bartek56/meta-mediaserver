SUMMARY = "certbot"
HOMEPAGE = "https://pypi.org/project/certbot/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=c718e64b2519bc0eac20e57e114a1219"
RDEPENDS:${PN} += " python3 python3-parsedatetime python3-pytz python3-distro python3-configargparse python3-pyrfc3339 python3-acme python3-josepy"
SRC_URI[sha256sum] = "4d573635840bbcc1124a2176e7188e69f6e3210f9ed94e20839547f07caee2b2"
PYPI_PACKAGE = "certbot"

inherit pypi setuptools3

