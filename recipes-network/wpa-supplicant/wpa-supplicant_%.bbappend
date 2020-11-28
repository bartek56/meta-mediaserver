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

    install -m 0755 ${WORKDIR}/wpa_supplicant.conf ${D}/etc

    rm ${D}/${systemd_system_unitdir}/wpa_supplicant-nl80211@.service
    rm ${D}/${systemd_system_unitdir}/wpa_supplicant-wired@.service

    install -d ${D}/etc/mediaserver
    ln -sf /etc/wpa_supplicant.conf ${D}/etc/mediaserver/wpa_supplicant.conf

}

FILES_${PN} += "${systemd_system_unitdir}/wpa_supplicant.service"

