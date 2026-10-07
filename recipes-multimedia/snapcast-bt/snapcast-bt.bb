SUMMARY = "Snpcast-bt"
DESCRIPTION = "Snapcast Bluetooth script to switch pa sink"
LICENSE = "CLOSED"



SRC_URI = " \
    file://bt-snapcast-autoplug.sh \
    file://bt-snapcast-autoplug.service \
    file://pa-event-generator.sh \
    file://pa-event-generator.service \
"

RDEPENDS:${PN} = "bash snapcast-server"


inherit systemd

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/bt-snapcast-autoplug.sh ${D}${bindir}
    install -m 0755 ${WORKDIR}/pa-event-generator.sh ${D}${bindir}

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/bt-snapcast-autoplug.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/pa-event-generator.service ${D}${systemd_system_unitdir}
}

SYSTEMD_SERVICE_${PN} = "bt-snapcast-autoplug.service pa-event-generator.service"
SYSTEMD_AUTO_ENABLE_${PN} = "enable"

FILES:${PN}-client = " \
    ${bindir}/snapclient \
    ${sysconfdir}/snapclient.conf \
    ${systemd_system_unitdir}/snapclient.service \
"

FILES:${PN}-client-doc = "${mandir}/man1/snapclient*"

FILES:${PN} = " \
    ${bindir}/bt-snapcast-autoplug.sh \
    ${systemd_system_unitdir}/bt-snapcast-autoplug.service \
    ${bindir}/pa-event-generator.sh \
    ${systemd_system_unitdir}/pa-event-generator.service \
"

FILES:${PN}-server-doc = "${mandir}/man1/snapserver*"