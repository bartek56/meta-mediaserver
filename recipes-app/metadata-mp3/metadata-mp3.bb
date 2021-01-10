SUMMARY = "Youtube downloader"
HOMEPAGE = "https://github.com/ytdl-org/youtube-dl"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE;md5=12a8965e31d96ba989d4294f1e2cd525"

#SRC_URI[sha256sum] = "a57bab1cfc3d57ae84e26e735daac498fd7b54261fe911e5ba58acfd0ed71742"

PYPI_PACKAGE = "metadata_mp3"
PYPI_SRC_URI = "file://metadata_mp3-1.0.tar.gz"

#S = "${WORKDIR}/metadata-mp3"
 
inherit pypi setuptools3

