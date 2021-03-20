SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[sha256sum] = "02432aa2dd0e859e64d74fca2ad624abf3bead3dba811d594100e1cb7897dce7"

PYPI_PACKAGE = "youtube_dl"
FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

