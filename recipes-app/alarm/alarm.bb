SUMMARY = "Alarm"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "bash mpc"

SRC_URI="file://alarm.service \
         file://alarm.sh \
         file://alarm.timer \
         file://alarm_snooze.timer \
         file://alarm_snooze.service \
         file://systemdVariables \
"

do_install(){
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/alarm.sh ${D}/opt
    
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.timer ${D}${systemd_system_unitdir}
    
    install -d ${D}${sysconfdir}/mediaserver
    install -m 0755 ${WORKDIR}/systemdVariables ${D}${sysconfdir}/mediaserver

    ln -sf /opt/alarm.sh ${D}${sysconfdir}/mediaserver/alarm.sh
    ln -sf ${systemd_system_unitdir}/alarm.timer ${D}${sysconfdir}/mediaserver/alarm.timer
    ln -sf ${systemd_system_unitdir}/alarm_snooze.timer ${D}${sysconfdir}/mediaserver/alarm_snooze.timer
}

FILES_${PN} += "/opt/alarm.sh"
FILES_${PN} += "${sysconfdir}/mediaserver/systemdVariables"
FILES_${PN} += "${systemd_system_unitdir}/*.service"
FILES_${PN} += "${systemd_system_unitdir}/*.timer"

