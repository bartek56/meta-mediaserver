SUMMARY = "certbot"
HOMEPAGE = "https://pypi.org/project/certbot/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=c718e64b2519bc0eac20e57e114a1219"
RDEPENDS:${PN} += " python3 python3-parsedatetime python3-pytz python3-distro python3-configargparse python3-pyrfc3339 python3-acme python3-josepy"
SRC_URI[sha256sum] = "4d573635840bbcc1124a2176e7188e69f6e3210f9ed94e20839547f07caee2b2"

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://certbot.service \
            file://certbot.timer"

PYPI_PACKAGE = "certbot"

inherit systemd pypi setuptools3

do_install:append () {
    install -d ${D}${systemd_system_unitdir}
    cp ${WORKDIR}/certbot.service ${D}${systemd_system_unitdir}
    cp ${WORKDIR}/certbot.timer ${D}${systemd_system_unitdir}
}

FILES:${PN} += "${systemd_system_unitdir}/certbot.service"
FILES:${PN} += "${systemd_system_unitdir}/certbot.timer"