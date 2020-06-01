SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/mpd:"
SRC_URI += "file://mpd.conf \
"
do_install_append() {
        install -d ${D}/etc
        install -m 0755 ${WORKDIR}/mpd.conf ${D}/etc
}

FILES_${PN} += "etc/mpd.conf"

