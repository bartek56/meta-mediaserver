SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/minidlna:"
SRC_URI += "file://minidlna.conf"

do_install_append() {
        install -m 0755 ${WORKDIR}/minidlna.conf ${D}/etc
}
