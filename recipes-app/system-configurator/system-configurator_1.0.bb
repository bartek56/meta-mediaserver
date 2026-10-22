SUMMARY = "Simple hostname and Ethernet configurator"
SECTION = "apps"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d244e0e001d37008058674881c787cc3"

SRC_URI = "file://LICENSE \
           file://system-configurator"

S = "${UNPACKDIR}"
inherit allarch

RDEPENDS:${PN} = "python3-core python3-modules systemd"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/system-configurator ${D}${bindir}
}

