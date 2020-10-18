SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[md5sum] = "c7df2f01e67898078fa774df106a3a4e"
SRC_URI[sha256sum] = "67fb9bfa30f5b8f06227c478a8a6ed04af1f97ad4e81dd7e2ce518df3e275391"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

