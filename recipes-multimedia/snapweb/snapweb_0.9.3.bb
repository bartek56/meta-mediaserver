SUMMARY = "Snapcast web interface"
DESCRIPTION = "Mobile-friendly web client for Snapcast"
HOMEPAGE = "https://github.com/snapcast/snapweb"
SECTION = "multimedia"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/GPL-3.0-only;md5=c79ff39f19dfec6d293b95dea7b07891"

SRC_URI = "https://github.com/snapcast/snapweb/releases/download/v${PV}/snapweb.zip"
SRC_URI[sha256sum] = "cc258df98b8c474ea19048bc84c0c2e2c5fbc3b0856aef03a838f3a4489fa4c7"

S = "${UNPACKDIR}"

do_install() {
    install -d ${D}${datadir}/snapserver/snapweb
    cp --no-preserve=ownership --recursive \
        ${UNPACKDIR}/. \
        ${D}${datadir}/snapserver/snapweb/
}

FILES:${PN} = "${datadir}/snapserver/snapweb"
