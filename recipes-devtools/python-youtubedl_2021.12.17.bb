SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[sha256sum] = "bc59e86c5d15d887ac590454511f08ce2c47698d5a82c27bfe27b5d814bbaed2"

PYPI_PACKAGE = "youtube_dl"

FILES:${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

