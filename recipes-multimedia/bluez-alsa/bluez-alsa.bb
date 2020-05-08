UMMARY = "Bluetooth Audio ALSA Backend"
HOMEPAGE = "https://github.com/Arkq/bluez-alsa"
SECTION = "devel"

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=72d868d66bdd5bf51fe67734431de057"

DEPENDS = "alsa-lib bluez5 dbus glib-2.0 sbc systemd"

SRCREV = "master"
SRC_URI = "git://github.com/Arkq/bluez-alsa.git;branch=master;protocol=https \
           file://bluez-alsa.service \
           file://bluealsa.service \
           file://bluealsa-aplay.service \
"

S = "${WORKDIR}/git"

inherit systemd pkgconfig autotools

do_install_append () {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/bluez-alsa.service ${D}${systemd_system_unitdir}

    install -m 0644 ${WORKDIR}/bluealsa.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/bluealsa-aplay.service ${D}${systemd_system_unitdir}
}

FILES_${PN} += "${libdir}/alsa-lib/lib*.so ${datadir}/alsa"
FILES_${PN}-dev += "${libdir}/alsa-lib/*.la"
FILES_${PN}-staticdev += "${libdir}/alsa-lib/lib*.a"
FILES_${PN}-dbg += "${libdir}/alsa-lib/.debug/*.so"

FILES_${PN} += "${systemd_system_unitdir}/bluealsa.service"
FILES_${PN} += "${systemd_system_unitdir}/bluealsa-aplay.service"

SYSTEMD_SERVICE_${PN} = "bluez-alsa.service"


