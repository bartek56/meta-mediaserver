SUMMARY = "certbot"
HOMEPAGE = "https://pypi.org/project/certbot/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=a6f5ef9903b6a5af9573a7c7572d3a31"
RDEPENDS:${PN} += " python3 python3-parsedatetime python3-pytz python3-distro python3-configargparse python3-pyrfc3339 python3-acme \
                    python3-josepy python3-configobj python3-pyopenssl"

SRC_URI[sha256sum] = "c896a0aa3fe1fa1e344002d4a24a5934889a88b8759f41a22b4dcfe5a8e27b94"

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://certbot.service \
            file://certbot.timer"

PYPI_PACKAGE = "certbot"

inherit systemd pypi setuptools3

do_install:append () {
    install -d ${D}${systemd_system_unitdir}
    cp ${UNPACKDIR}/certbot.service ${D}${systemd_system_unitdir}
    cp ${UNPACKDIR}/certbot.timer ${D}${systemd_system_unitdir}
}

FILES:${PN} += "${systemd_system_unitdir}/certbot.service"
FILES:${PN} += "${systemd_system_unitdir}/certbot.timer"
