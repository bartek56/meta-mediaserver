SUMMARY = "FileBrowser"
LICENSE = "CLOSED"
#LIC_FILES_CHKSUM = "file://LICENSE;md5=7246f848faa4e9c9fc0ea91122d6e680"

DEPENDS += " python-mutagen python-youtubedl"
RDEPENDS_${PN} += "bash"
SRC_URI="https://github.com/filebrowser/filebrowser/releases/download/v2.1.0/linux-armv7-filebrowser.tar.gz \
         file://filebrowser.service"

S = "${WORKDIR}"

SRC_URI[md5sum] = "02ff427564c9002b70a02bab04887f31"
SRC_URI[sha256sum] = "87451de51f2b230a095225c450a846da48c4f7589c2524cb8b4693a215ad3dff"

inherit systemd

do_install_append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/*.service ${D}${systemd_unitdir}/system
}

do_install(){
    install -d ${D}/usr/bin
    install -m 0644 ${S}/filebrowser ${D}/usr/bin
}

FILES_${PN} += "/usr/bin/filebrowser"
FILES_${PN} += "${systemd_unitdir}/system/*.service"

