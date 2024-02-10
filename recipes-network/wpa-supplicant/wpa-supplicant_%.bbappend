SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://wpa_supplicant.service \
            file://wpa_supplicant.conf \
            file://10-wired.network \
            file://20-wireless.network \
           "

inherit systemd

SYSTEMD_AUTO_ENABLE = "enable" 
SYSTEMD_SERVICE:${PN} = "wpa_supplicant.service"


do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/wpa_supplicant.service ${D}${systemd_system_unitdir}

    install -m 0755 ${WORKDIR}/wpa_supplicant.conf ${D}/etc

    rm ${D}/${systemd_system_unitdir}/wpa_supplicant-nl80211@.service
    rm ${D}/${systemd_system_unitdir}/wpa_supplicant-wired@.service

    install -d ${D}/etc/systemd/network
    install -m 0755 ${WORKDIR}/10-wired.network ${D}/etc/systemd/network
    install -m 0755 ${WORKDIR}/20-wireless.network ${D}/etc/systemd/network
  

    install -d ${D}/etc/mediaserver
    ln -sf /etc/wpa_supplicant.conf ${D}/etc/mediaserver/wpa_supplicant.conf
    ln -sf /etc/systemd/network/10-wired.network ${D}/etc/mediaserver/10-wired.network
    ln -sf /etc/systemd/network/20-wireless.network ${D}/etc/mediaserver/20-wireless.network

}

FILES:${PN} += "${systemd_system_unitdir}/wpa_supplicant.service"

