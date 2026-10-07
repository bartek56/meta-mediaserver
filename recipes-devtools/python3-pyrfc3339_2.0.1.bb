SUMMARY = "pyRFC3339"
HOMEPAGE = "https://pypi.org/project/pyRFC3339/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://PKG-INFO;md5=2de7e29c3932b1f420f1366cce825ba2"
RDEPENDS:${PN} += " python3"

SRC_URI[sha256sum] = "e47843379ea35c1296c3b6c67a948a1a490ae0584edfcbdea0eaffb5dd29960b"

PYPI_PACKAGE = "pyrfc3339"


inherit pypi setuptools3

