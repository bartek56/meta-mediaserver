SUMMARY = "WikiQuote"
HOMEPAGE = "https://pypi.org/project/wikiquote/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=98bd81ca37b5f094c1673bc02b7003e0"
RDEPENDS:${PN} += " python3-lxml"

SRC_URI[md5sum] = "732689f7fff232d4b69303341baddfbb"
SRC_URI[sha256sum] = "cabf43c0275c29b64daed7216a16714c28377b73ad3b0ec9c7c54f3e607fc47b"

PYPI_PACKAGE = "wikiquote"

FILES:${PN} += "${datadir}/etc/*"

inherit pypi setuptools3

do_configure:prepend() {
    find ${WORKDIR}/wikiquote-0.1.14 -name setup.py | xargs sed -i 's~from distutils.core import setup~from setuptools import setup~g'
}
