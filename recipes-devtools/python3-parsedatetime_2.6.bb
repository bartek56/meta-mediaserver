SUMMARY = "ParseDateTime"
HOMEPAGE = "https://pypi.org/project/pyRFC3339/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://PKG-INFO;md5=d276d713ae864d7eee22312e0e3d6834"
RDEPENDS:${PN} += " python3"

SRC_URI[sha256sum] = "4cb368fbb18a0b7231f4d76119165451c8d2e35951455dfee97c62a87b04d455"

PYPI_PACKAGE = "parsedatetime"


inherit pypi setuptools3

