SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[md5sum] = "b2ddcefe8a7f30260f8f22ededcc56db"
SRC_URI[sha256sum] = "1b098b7ae41551f46dbae70e56dbabdf39c8faf50e072d0c0b42c44d64afebf8"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

