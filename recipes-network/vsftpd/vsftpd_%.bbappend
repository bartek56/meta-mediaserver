SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://vsftpd.service \
            file://ftpd.passwd \
            file://vsftpd \
            file://vsftpd.conf \
"
RDEPENDS_${PN} += " pam-pwdfile"

inherit systemd

SYSTEMD_PACKAGES = "${PN}" 

do_install_append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/vsftpd.service ${D}${systemd_system_unitdir}
        install -d ${D}/etc
        install -m 0644 ${WORKDIR}/vsftpd.conf ${D}/etc
        install -d ${D}/etc/vsftpd
        install -m 0644 ${WORKDIR}/ftpd.passwd ${D}/etc/vsftpd
}

