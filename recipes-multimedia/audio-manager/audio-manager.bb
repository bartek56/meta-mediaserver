SUMMARY = "Snapcast Bluetooth audio manager"
DESCRIPTION = "Event-driven audio manager for Snapcast, Bluetooth, PulseAudio, and MPD"
LICENSE = "CLOSED"

FILESEXTRAPATHS:prepend := "${THISDIR}/audio-manager:"



SRC_URI = " \
    file://audio-manager.py \
    file://audio_manager/__init__.py \
    file://audio_manager/adapters.py \
    file://audio_manager/app.py \
    file://audio_manager/audio.py \
    file://audio_manager/avahi.py \
    file://audio_manager/events.py \
    file://audio_manager/lifecycle.py \
    file://audio_manager/models.py \
    file://audio_manager/monitoring.py \
    file://audio_manager/persistence.py \
    file://audio_manager/registry.py \
    file://audio_manager/scheduler.py \
    file://audio-manager.service \
"

S = "${UNPACKDIR}"

RDEPENDS:${PN} = " \
    python3-core \
    python3-dbus \
    python3-pygobject \
    python3-pulsectl \
    pulseaudio-misc \
    snapcast-server \
"


inherit systemd python3-dir

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${UNPACKDIR}/audio-manager.py ${D}${bindir}

    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/audio_manager
    install -m 0644 ${UNPACKDIR}/audio_manager/*.py \
        ${D}${PYTHON_SITEPACKAGES_DIR}/audio_manager/

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/audio-manager.service ${D}${systemd_system_unitdir}
}

SYSTEMD_SERVICE:${PN} = "audio-manager.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

FILES:${PN}-client = " \
    ${bindir}/snapclient \
    ${sysconfdir}/snapclient.conf \
    ${systemd_system_unitdir}/snapclient.service \
"

FILES:${PN}-client-doc = "${mandir}/man1/snapclient*"

FILES:${PN} = " \
    ${bindir}/audio-manager.py \
    ${PYTHON_SITEPACKAGES_DIR}/audio_manager/*.py \
    ${systemd_system_unitdir}/audio-manager.service \
"
