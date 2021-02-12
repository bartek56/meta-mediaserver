SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"


SRC_URI[md5sum] = "378d82eb3e539019bf5d5c2d8c5082da"
SRC_URI[sha256sum] = "933519ab7d2fa05bd28f8443a2115d21efd0355c051986548af9f233e300db0b"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

