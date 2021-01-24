SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[md5sum] = "7414111937c54b7d8334791b713b0b18"
SRC_URI[sha256sum] = "acf74701a31b6c3d06f9d4245a46ba8fb6c378931681177412043c6e8276fee7"

PYPI_PACKAGE = "youtube_dl"

FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

