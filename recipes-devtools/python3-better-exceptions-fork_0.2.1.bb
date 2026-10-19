SUMMARY = "better exceptions"
HOMEPAGE = "https://pypi.org/project/better-exceptions-fork/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=dec719bb473c830569074d447f12add9"

RDEPENDS:${PN} = "python3-pygments"

PYPI_SRC_URI = "git://github.com/Delgan/better-exceptions.git;protocol=https;branch=master_fork"
SRCREV = "1b8502128466ee770e273523dd724b7db4526f71"
PYPI_PACKAGE = "better-exceptions-fork"

inherit pypi setuptools3

S = "${UNPACKDIR}/python3-better-exceptions-fork-${PV}"
