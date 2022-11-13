SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://smb.conf "

do_install:append() {
    install -m 0755 ${WORKDIR}/smb.conf ${D}/etc/samba

    install -d ${D}/etc/mediaserver
    ln -sf /etc/mediaserver/smb.conf ${D}/etc/samba/smb.conf
}

