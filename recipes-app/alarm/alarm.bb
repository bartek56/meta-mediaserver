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

#SRC_URI[md5sum] = "a6add4bac7d21b2b210987ab1cda7674"
#SRC_URI[sha256sum] = "bdf7338df04d3f44c62fbf8322d4d38e2317e9bc2bb5277ccf2214761e8d0de1"
#inherit systemd

#SYSTEMD_PACKAGES = "${PN}" 

do_install(){
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/alarm.sh ${D}/opt
    
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/*.timer ${D}${systemd_system_unitdir}
    
    install -d ${D}/etc/mediaserver
    install -m 0755 ${WORKDIR}/systemdVariables ${D}/etc/mediaserver

    ln -sf /opt/alarm.sh ${D}/etc/mediaserver/alarm.sh
    ln -sf ${systemd_system_unitdir}/alarm.timer ${D}/etc/mediaserver/alarm.timer
    ln -sf ${systemd_system_unitdir}/alarm_snooze.timer ${D}/etc/mediaserver/alarm_snooze.timer
}

FILES_${PN} += "/opt/alarm.sh"
FILES_${PN} += "/etc/mediaserver/systemdVariables"
FILES_${PN} += "${systemd_system_unitdir}/*.service"
FILES_${PN} += "${systemd_system_unitdir}/*.timer"

