SUMMARY = "Danfoss thermostat"
LICENSE = "CLOSED"

RDEPENDS:${PN} += " python3-libetrv"

SRC_URI="file://danfoss.py"

do_install(){
    install -d ${D}/opt
    install -m 0755 ${WORKDIR}/danfoss.py ${D}/opt
}

FILES:${PN} += "/opt/danfoss.py"

