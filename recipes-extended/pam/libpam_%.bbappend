SUMMARY = "libpam - config environment"
FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"
SRC_URI += "file://environment"


do_install:append() {
        install -m 0644 ${WORKDIR}/environment ${D}${sysconfdir}
}

