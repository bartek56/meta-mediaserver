SUMMARY = "Config Script"
LICENSE = "CLOSED"

RDEPENDS_${PN} += " bash"

SRC_URI="https://raw.githubusercontent.com/bartek56/LinuxEmbedded/master/scripts/installScriptYocto.sh"

SRC_URI[md5sum] = "84c9136baf35aa9247a8cda98afb2fe0"
SRC_URI[sha256sum] = "587c4ebaad64f3c0d1c40a1a90d08187fd23c0cc65b3c135e020e4beca797201"


do_install(){
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/installScriptYocto.sh ${D}/opt
}

FILES_${PN} += "/opt/installScriptYocto.sh"

