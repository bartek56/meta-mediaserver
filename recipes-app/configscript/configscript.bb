SUMMARY = "Config Script"
LICENSE = "CLOSED"

RDEPENDS:${PN} += " bash"

#TODO check by image target which one script should be included

SRC_URI="file://installScriptQt5.sh"
#SRC_URI="file://installScriptBase.sh"

do_install(){
    install -d ${D}/opt

    install -m 0755 ${WORKDIR}/installScriptBase.sh ${D}/opt/installScript.sh
    install -d ${D}/home/Documents
    install -d ${D}/home/Downloads
}

FILES:${PN} += "/opt/installScript.sh"
FILES:${PN} += "/home/Documents"
FILES:${PN} += "/home/Downloads"

