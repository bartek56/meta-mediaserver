SUMMARY = "Jellyfin media compatibility checker"
DESCRIPTION = "Read-only FFprobe based media compatibility checker with Jellyfin client profiles and FFmpeg recommendations"
HOMEPAGE = "https://jellyfin.org/docs/general/clients/codec-support/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=dbfc0588ce28c2525ae8bc8ad5c5f19e"

SRC_URI = "file://jellyfin-checker/"

S = "${UNPACKDIR}/jellyfin-checker"

RDEPENDS:${PN} = " \
    python3-core \
    python3-crypt \
    python3-datetime \
    python3-email \
    python3-io \
    python3-json \
    python3-netclient \
    python3-numbers \
    ffmpeg \
"

inherit python3-dir

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/main.py ${D}${bindir}/jellyfin-checker

    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/jellyfin_checker/data/profiles/general
    install -m 0644 ${S}/jellyfin_checker/*.py \
        ${D}${PYTHON_SITEPACKAGES_DIR}/jellyfin_checker/
    install -m 0644 ${S}/jellyfin_checker/data/profiles/general/*.json \
        ${D}${PYTHON_SITEPACKAGES_DIR}/jellyfin_checker/data/profiles/general/

    install -d ${D}${datadir}/doc/${PN}
    install -m 0644 ${S}/README.md ${D}${datadir}/doc/${PN}/README.md
}

FILES:${PN} += " \
    ${bindir}/jellyfin-checker \
    ${PYTHON_SITEPACKAGES_DIR}/jellyfin_checker/*.py \
    ${PYTHON_SITEPACKAGES_DIR}/jellyfin_checker/data/profiles/general/*.json \
    ${datadir}/doc/${PN}/README.md \
"
