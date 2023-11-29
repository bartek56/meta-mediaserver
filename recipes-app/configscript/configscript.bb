SUMMARY = "Config Script"
LICENSE = "CLOSED"

RDEPENDS:${PN} += " bash"

INSTALL_SCRIPT_NAME = '${@bb.utils.contains("DISTRO_FEATURES", "qt5", "installScriptQt5.sh", "installScriptBase.sh", d)}'

SRC_URI="file://${INSTALL_SCRIPT_NAME}"


do_install(){
    install -d ${D}/opt

    install -m 0755 ${WORKDIR}/${INSTALL_SCRIPT_NAME} ${D}/opt/installScript.sh
    install -d ${D}/home/Documents
    install -d ${D}/home/Downloads
}

FILES:${PN} += "/opt/installScript.sh"
FILES:${PN} += "/home/Documents"
FILES:${PN} += "/home/Downloads"

