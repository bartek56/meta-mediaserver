SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://smb.conf "

do_install:append() {
    install -d ${D}/etc/mediaserver
    install -m 0755 ${WORKDIR}/smb.conf ${D}/etc/mediaserver
    
    ln -sf /etc/mediaserver/smb.conf ${D}/etc/samba/smb.conf
}

