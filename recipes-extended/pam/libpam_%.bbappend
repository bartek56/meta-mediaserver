SUMMARY = "libpam - config environment"
FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://environment"


do_install_append() {
        install -m 0644 ${WORKDIR}/environment ${D}${sysconfdir}
}

