SUMMARY = "Snpcast-bt"
DESCRIPTION = "Snapcast Bluetooth script to switch pa sink"
LICENSE = "CLOSED"



SRC_URI = " \
    file://audio-manager.py \
    file://audio-manager.service \
    file://pa-event-generator.sh \
    file://pa-event-generator.service \
"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = " \
    python3-core \
    python3-dbus \
    python3-pygobject \
    python3-mpd2 \
    python3-pulsectl \
    pulseaudio-misc \
    snapcast-server \
"


inherit systemd

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${UNPACKDIR}/audio-manager.py ${D}${bindir}
    install -m 0755 ${UNPACKDIR}/pa-event-generator.sh ${D}${bindir}

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/audio-manager.service ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/pa-event-generator.service ${D}${systemd_system_unitdir}
}

SYSTEMD_SERVICE:${PN} = "audio-manager.service pa-event-generator.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

FILES:${PN}-client = " \
    ${bindir}/snapclient \
    ${sysconfdir}/snapclient.conf \
    ${systemd_system_unitdir}/snapclient.service \
"

FILES:${PN}-client-doc = "${mandir}/man1/snapclient*"

FILES:${PN} = " \
    ${bindir}/audio-manager.py \
    ${systemd_system_unitdir}/audio-manager.service \
    ${bindir}/pa-event-generator.sh \
    ${systemd_system_unitdir}/pa-event-generator.service \
"

FILES:${PN}-server-doc = "${mandir}/man1/snapserver*"
