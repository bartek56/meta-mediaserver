SUMMARY = "yt-dlp is a youtube-dl fork based on the now inactive youtube-dlc"
HOMEPAGE = "https://github.com/yt-dlp/yt-dlp"
LICENSE = "Apache"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

SRC_URI = "https://github.com/yt-dlp/yt-dlp/releases/download/${PV}/yt-dlp.tar.gz"

SRC_URI[sha256sum] = "e08331fb9a36eba56b4efd074b5b25fbf08413e9cb47009a28ecbffe47150310"

do_fetch[nostamp] = "1"

S = "${WORKDIR}/yt-dlp"
inherit python3-dir

do_compile() {
    echo "It's not needed"
}

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/yt_dlp
    cp -r ${S}/yt_dlp/* ${D}${PYTHON_SITEPACKAGES_DIR}/yt_dlp

    install -d ${D}${bindir}
    install -m 0755 ${S}/yt-dlp ${D}${bindir}/yt-dlp
}

FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/yt_dlp/*"
FILES:${PN} += "${bindir}/yt-dlp"
