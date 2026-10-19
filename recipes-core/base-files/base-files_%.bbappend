FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " file://hosts"

do_install:append () {
    install -m 0644 ${UNPACKDIR}/hosts ${D}${sysconfdir}/hosts
}

