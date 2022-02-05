SUMMARY = "Danfoss thermostat"
LICENSE = "CLOSED"

RDEPENDS_${PN} += " python3-libetrv"

SRC_URI="file://danfoss.py"

do_install(){
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/danfoss.py ${D}/opt
}

FILES_${PN} += "/opt/danfoss.py"

