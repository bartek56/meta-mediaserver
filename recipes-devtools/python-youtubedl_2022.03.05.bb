SUMMARY = "Youtube-dl"
HOMEPAGE = "github.com/ytdl-org/youtube-dl"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

PYPI_PACKAGE = "metadata_mp3"
SRCREV = "6508688e88c83bb811653083db9351702cd39a6a"
PYPI_SRC_URI = "git://github.com/ytdl-org/youtube-dl;protocol=https;branch=master"
 

inherit pypi setuptools3

S = "${WORKDIR}/git"

do_install_append(){
    rm -r ${D}/usr/share/etc/bash_completion.d
    rm -r ${D}/usr/share/etc/fish/completions
    rm -r ${D}/usr/share/etc/fish
    rm -r ${D}//usr/share/etc
}

