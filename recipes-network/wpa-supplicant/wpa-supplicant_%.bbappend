SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://wpa_supplicant.service \
            file://wpa_supplicant.conf \
            file://10-wired.network \
            file://20-wireless.network \
            file://systemd-networkd-wait-online.service.d/10-mediaserver-any.conf \
           "

inherit systemd

SYSTEMD_AUTO_ENABLE = "enable" 
SYSTEMD_SERVICE:${PN} = "wpa_supplicant.service"


do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/wpa_supplicant.service ${D}${systemd_system_unitdir}

    install -m 0755 ${UNPACKDIR}/wpa_supplicant.conf ${D}/etc

    rm ${D}/${systemd_system_unitdir}/wpa_supplicant-nl80211@.service
    rm ${D}/${systemd_system_unitdir}/wpa_supplicant-wired@.service

    install -d ${D}/etc/systemd/network
    install -m 0755 ${UNPACKDIR}/10-wired.network ${D}/etc/systemd/network
    install -m 0755 ${UNPACKDIR}/20-wireless.network ${D}/etc/systemd/network

    install -d ${D}${systemd_system_unitdir}/systemd-networkd-wait-online.service.d
    sed -e 's|@SYSTEMD_NETWORKD_WAIT_ONLINE@|${libexecdir}/systemd/systemd-networkd-wait-online|g' \
        ${UNPACKDIR}/systemd-networkd-wait-online.service.d/10-mediaserver-any.conf \
        > ${D}${systemd_system_unitdir}/systemd-networkd-wait-online.service.d/10-mediaserver-any.conf
    chmod 0644 ${D}${systemd_system_unitdir}/systemd-networkd-wait-online.service.d/10-mediaserver-any.conf
  

    install -d ${D}/etc/mediaserver
    ln -sf /etc/wpa_supplicant.conf ${D}/etc/mediaserver/wpa_supplicant.conf
    ln -sf /etc/systemd/network/10-wired.network ${D}/etc/mediaserver/10-wired.network
    ln -sf /etc/systemd/network/20-wireless.network ${D}/etc/mediaserver/20-wireless.network

}

FILES:${PN} += " \
    ${systemd_system_unitdir}/wpa_supplicant.service \
    ${systemd_system_unitdir}/systemd-networkd-wait-online.service.d/10-mediaserver-any.conf \
"
