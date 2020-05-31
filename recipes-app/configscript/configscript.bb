SUMMARY = "Config Script"
LICENSE = "CLOSED"

RDEPENDS_${PN} += " bash"

SRC_URI="file://installScriptYocto.sh"

do_install(){
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/installScriptYocto.sh ${D}/opt
}

FILES_${PN} += "/opt/installScriptYocto.sh"

