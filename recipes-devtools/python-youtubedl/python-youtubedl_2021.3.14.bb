SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI[md5sum] = "38ad456faf10b54b78804c13dfde7c91"
SRC_URI[sha256sum] = "c287ad8dd33471aabaabab5ab1dd825bebc70eb8b83ebfa93fd71022e01a1d08"

PYPI_PACKAGE = "youtube_dl"

FILES_${PN} += "${datadir}/etc/*"
inherit pypi setuptools3

