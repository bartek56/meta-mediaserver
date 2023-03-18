SUMMARY = "yt-dlp is a youtube-dl fork based on the now inactive youtube-dlc"
HOMEPAGE = "https://github.com/yt-dlp/yt-dlp"
LICENSE = "Apache"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

PYPI_SRC_URI = "https://github.com/yt-dlp/yt-dlp/releases/download/${PV}/yt-dlp.tar.gz"

SRC_URI[sha256sum] = "99db0ab54b986aa5c5bb145dc1cf0e516612e61cdb964ee274dddceeceae98a9"
PYPI_PACKAGE = "yt-dlp"

inherit pypi setuptools3

S = "${WORKDIR}/yt-dlp"

FILES:${PN} += "/usr/share/bash-completion/completions/yt-dlp"
FILES:${PN} += "/usr/share/zsh/site-functions/_yt-dlp"
FILES:${PN} += "/usr/share/fish/vendor_completions.d/yt-dlp.fish"
