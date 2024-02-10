SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://vsftpd.service \
            file://ftpd.passwd \
            file://vsftpd \
            file://vsftpd.conf \
            file://bartosz \
"

RDEPENDS:${PN} += " pam-pwdfile"

inherit systemd useradd

#SYSTEMD_PACKAGES = "${PN}" 
SYSTEMD_SERVICE:${PN} = "vsftpd.service"

USERADD_PACKAGES = "${PN}"
USERADD_PARAM_${PN} = "-d /home/vsftpd -s /bin/false -G nogroup -U vsftpd"

do_install:append() {
        install -d ${D}${systemd_system_unitdir}
        install -m 0644 ${WORKDIR}/vsftpd.service ${D}${systemd_system_unitdir}

        install -d ${D}/etc
        install -m 0644 ${WORKDIR}/vsftpd.conf ${D}/etc

        install -d ${D}/etc/vsftpd
        install -m 0644 ${WORKDIR}/ftpd.passwd ${D}/etc/vsftpd

        install -d ${D}/etc/vsftpd_user_conf
        install -m 0644 ${WORKDIR}/bartosz ${D}/etc/vsftpd_user_conf

        install -m 0644 ${WORKDIR}/vsftpd ${D}/etc/pam.d/vsftpd
}

