SUMMARY = "Textual system configurator for MediaServer and MediaClient"
SECTION = "apps"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d244e0e001d37008058674881c787cc3"

SRC_URI = "file://LICENSE \
           file://system_configurator.py \
           file://system_configurator_ui.py \
           file://system-configurator \
           file://system-configurator.service"

S = "${UNPACKDIR}"
inherit allarch systemd

RDEPENDS:${PN} = " \
    python3-core \
    python3-json \
    python3-modules \
    python3-rich \
    python3-markdown-it-py \
    python3-mdit-py-plugins \
    python3-linkify-it-py \
    python3-platformdirs \
    python3-typing-extensions \
    textual \
    systemd \
    util-linux \
"

SYSTEMD_SERVICE:${PN} = "system-configurator.service"
SYSTEMD_AUTO_ENABLE = "disable"

do_install() {
    install -d ${D}${libexecdir}/system-configurator
    install -m 0755 ${S}/system_configurator.py ${D}${libexecdir}/system-configurator
    install -m 0755 ${S}/system_configurator_ui.py ${D}${libexecdir}/system-configurator

    install -d ${D}${bindir}
    install -m 0755 ${S}/system-configurator ${D}${bindir}

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${S}/system-configurator.service ${D}${systemd_system_unitdir}
}

FILES:${PN} += "${libexecdir}/system-configurator/* ${systemd_system_unitdir}/system-configurator.service"

