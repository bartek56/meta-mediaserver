SUMMARY = "Alarm"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "bash mpc"

SRC_URI="file://alarm.service \
         file://alarm.sh \
         file://alarm.timer \
         file://alarm_snooze.timer \
         file://alarm_snooze.service \
"

do_install(){
    install -d ${D}/opt
    install -m 0775 ${WORKDIR}/alarm.sh ${D}/opt

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_system_unitdir}
    install -m 0775 ${WORKDIR}/*.timer ${D}${systemd_system_unitdir}
   
    install -d ${D}${sysconfdir}/mediaserver
    ln -sf /opt/alarm.sh ${D}${sysconfdir}/mediaserver/alarm.sh
    ln -sf ${systemd_system_unitdir}/alarm.timer ${D}${sysconfdir}/mediaserver/alarm.timer
    ln -sf ${systemd_system_unitdir}/alarm_snooze.timer ${D}${sysconfdir}/mediaserver/alarm_snooze.timer
}

FILES:${PN} += "/opt/alarm.sh"
FILES:${PN} += "${systemd_system_unitdir}/*.service"
FILES:${PN} += "${systemd_system_unitdir}/*.timer"
