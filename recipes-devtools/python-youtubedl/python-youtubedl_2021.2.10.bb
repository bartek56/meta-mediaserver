SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[md5sum] = "41c761c44c13ffcdccac510151ccf7d6"
SRC_URI[sha256sum] = "b390cddbd4d605bd887d0d4063988cef0fa13f916d2e1e3564badbb22504d754"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

