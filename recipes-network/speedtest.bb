SUMMARY = "SpeedTest"
LICENSE = "CLOSED"

SRC_URI="https://install.speedtest.net/app/cli/ookla-speedtest-1.0.0-aarch64-linux.tgz"

S = "${WORKDIR}"

SRC_URI[sha256sum] = "073684dc3490508ca01b04c5855e04cfd797fed33f6ea6a6edc26dfbc6f6aa9e"

do_install(){
    install -d ${D}${bindir}
    install -m 0644 ${S}/speedtest ${D}${bindir}/
}

FILES_${PN} += "${bindir}/speedtest"


