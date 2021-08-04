SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[sha256sum] = "cb2d3ee002158ede783e97a82c95f3817594df54367ea6a77ce5ceea4772f0ab"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

