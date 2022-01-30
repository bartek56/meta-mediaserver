SUMMARY = "pygments"
HOMEPAGE = "https://pypi.org/project/pygments/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=eba1d3e6e8728f9179aa1d097f137465"

SRC_URI[sha256sum] = "2ff53b96fae81588e6f4f9147cb45af7d321c67335e5d794f6838f1710154598"

PYPI_SRC_URI = "https://github.com/pygments/pygments/archive/refs/tags/${PV}.tar.gz"
PYPI_PACKAGE = "pygments"

inherit pypi setuptools3

