SUMMARY = "PulseAudio config"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://pulseaudio.service \
            file://system.pa"

inherit systemd 

SYSTEMD_SERVICE_${PN} = "pulseaudio.service"
SYSTEMD_PACKAGES = "${PN}" 

do_install_append() {
        install -d ${D}${systemd_unitdir}/system
        install -m 0755 ${WORKDIR}/pulseaudio.service ${D}${systemd_unitdir}/system

        install -d ${D}/etc/pulse
        install -m 0755 ${WORKDIR}/system.pa ${D}/etc/pulse
}

FILES_${PN} += "${systemd_system_unitdir}/*.service"

