SUMMARY = "ConfigArgParse"
HOMEPAGE = "https://pypi.org/project/pyRFC3339/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://PKG-INFO;md5=f048c979c32b6b1b0b30c639d8a2e3e0"
RDEPENDS:${PN} += " python3"

SRC_URI[sha256sum] = "e7067471884de5478c58a511e529f0f9bd1c66bfef1dea90935438d6c23306d1"

PYPI_PACKAGE = "ConfigArgParse"


inherit pypi setuptools3

