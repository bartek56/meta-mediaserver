SUMMARY = "Config Script"
LICENSE = "CLOSED"

RDEPENDS:${PN} += " bash"

SRC_URI="file://installScriptYocto.sh"

do_install(){
    install -d ${D}/opt

    install -m 0755 ${WORKDIR}/installScriptYocto.sh ${D}/opt
    install -d ${D}/home/Documents
    install -d ${D}/home/Downloads
}

FILES:${PN} += "/opt/installScriptYocto.sh"
FILES:${PN} += "/home/Documents"
FILES:${PN} += "/home/Downloads"

