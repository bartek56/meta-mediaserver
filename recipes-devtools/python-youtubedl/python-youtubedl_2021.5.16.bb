SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[md5sum] = "085f150c7507e6eecdd2510d58940c7f"
SRC_URI[sha256sum] = "4e569cb0477428fd96ee6f7e7a6640b7c9416be626ed708ac4b8ada6c5a6ffbe"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

