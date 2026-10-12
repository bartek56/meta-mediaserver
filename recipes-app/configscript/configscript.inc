SUMMARY = "Config Script"
LICENSE = "CLOSED"

FILESEXTRAPATHS:prepend := "${THISDIR}/configscript:"

RDEPENDS:${PN} += "bash"

SRC_URI = " \
    file://${INSTALL_SCRIPT_NAME} \
    file://installCommon.sh \
"

do_install() {
    install -d ${D}/opt
    install -m 0755 ${UNPACKDIR}/${INSTALL_SCRIPT_NAME} ${D}/opt/installScript.sh
    install -m 0644 ${UNPACKDIR}/installCommon.sh ${D}/opt/installCommon.sh
    install -d ${D}/home/Documents
    install -d ${D}/home/Downloads
}

FILES:${PN} += " \
    /opt/installScript.sh \
    /opt/installCommon.sh \
    /home/Documents \
    /home/Downloads \
"
