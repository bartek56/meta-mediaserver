SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://wpa_supplicant.service \
            file://wpa_supplicant.conf "

inherit systemd

SYSTEMD_PACKAGES = "${PN}" 
SYSTEMD_SERVICE_${PN} = "wpa_supplicant.service"


do_install_append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/wpa_supplicant.service ${D}${systemd_system_unitdir}

        install -m 0644 ${WORKDIR}/wpa_supplicant.conf ${D}/etc

        rm ${D}/${systemd_system_unitdir}/wpa_supplicant-nl80211@.service
        rm ${D}/${systemd_system_unitdir}/wpa_supplicant-wired@.service
}

FILES_${PN} += "${systemd_system_unitdir}/wpa_supplicant.service"

