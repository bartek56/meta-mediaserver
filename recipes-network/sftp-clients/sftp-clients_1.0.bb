SUMMARY = "SFTP clients -  group of scripts to enable sftp file sharing with the new users"
LICENSE = "CLOSED"

RDEPENDS:${PN} += " bash"

SRC_URI="file://sftpUsers \
         file://mountShared \
         file://mount_shared.service"

inherit systemd


SYSTEMD_SERVICE:${PN} = "mount_shared.service"

do_install(){
    #install -d ${D}${bindir}
    #install -m 0644 ${WORKDIR}/sftpUsers ${D}${bindir}
    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/sftpUsers ${D}/opt
    install -m 0644 ${WORKDIR}/mountShared ${D}/opt

    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/mount_shared.service ${D}${systemd_unitdir}/system

    install -d ${D}/home/sftp_users
}

FILES:${PN} += "opt/sftpUsers"
FILES:${PN} += "opt/mountShared"
FILES:${PN} += "/home/sftp_users"
