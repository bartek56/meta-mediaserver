SUMMARY = "yt-dlp is a youtube-dl fork based on the now inactive youtube-dlc"
HOMEPAGE = "https://github.com/yt-dlp/yt-dlp"
LICENSE = "Apache"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

PYPI_SRC_URI = "https://github.com/yt-dlp/yt-dlp/releases/download/${PV}/yt-dlp.tar.gz"
RDEPENDS_${PN} = " python3-fire python3-bluepy python3-xxtea python3-loguru python3-cstruct python3-pytest"

SRC_URI[sha256sum] = "51fa055912c7fc742a882ff58236bd25b39055b98168a3563ed17cc575c3c3ae"

PYPI_PACKAGE = "yt-dlp"

inherit pypi setuptools3

S = "${WORKDIR}/yt-dlp"

FILES:${PN} += "/usr/share/bash-completion/completions/yt-dlp"
FILES:${PN} += "/usr/share/zsh/site-functions/_yt-dlp"
FILES:${PN} += "/usr/share/fish/vendor_completions.d/yt-dlp.fish"

