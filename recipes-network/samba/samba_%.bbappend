SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://smb.conf "

do_install_append() {
    install -m 0755 ${WORKDIR}/smb.conf ${D}/etc/samba

    install -d ${D}/etc/mediaserver
    ln -sf /etc/samba/smb.conf ${D}/etc/mediaserver/smb.conf
}

