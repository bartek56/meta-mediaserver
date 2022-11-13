SUMMARY = "better exceptions"
HOMEPAGE = "https://pypi.org/project/better-exceptions-fork/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=dec719bb473c830569074d447f12add9"

SRC_URI[sha256sum] = "1836d3d31a843c69f4a9cb0b7cbe9256dc04eac3618a59dbd178f8e8ceaaaf10"

RDEPENDS:${PN} = "python3-pygments"

PYPI_SRC_URI = "https://github.com/Delgan/better-exceptions/archive/refs/tags/${PV}.post6.tar.gz"
PYPI_PACKAGE = "better-exceptions-fork"

inherit pypi setuptools3

S = "${WORKDIR}/better-exceptions-0.2.1.post6"

