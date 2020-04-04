LICENSE = "CLOSED"

SRCREV = "${AUTOREV}"

SRC_URI="git://github.com/tiwe-de/libpam-pwdfile"

SRC_URI[md5sum] = "301198b555261dae57f5a300176c1f8e"
SRC_URI[sha256sum] = "f59a386ea67dd0acebff3ae5d5a2d91021c05b241e7e135fc82006ca198df844"

DEPENDS = "libpam"

S = "${WORKDIR}/git"

do_install(){
    install -d ${D}/lib/security
    install -m 0644 ${S}/pam_pwdfile.so ${D}/lib/security
}

FILES_${PN} += "lib/security/pam_pwdfile.so"
#FILES_${PN} += "${systemd_unitdir}/system/*.service"


