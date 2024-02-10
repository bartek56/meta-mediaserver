SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/bartek56/metadata_mp3"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=0539da39d79143b7b250cf89ae1299b1"

PYPI_PACKAGE = "metadata_mp3"
SRCREV = "${AUTOREV}"
PYPI_SRC_URI = "git://github.com/bartek56/metadata_mp3;protocol=https;branch=main"


inherit pypi setuptools3

S = "${WORKDIR}/git"
