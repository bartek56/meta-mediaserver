SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://smb.conf "

do_install_append() {
        install -m 0644 ${WORKDIR}/smb.conf ${D}/etc/samba
}

FILES_${PN} += "${systemd_system_unitdir}/wpa_supplicant.service"

