SUMMARY = "FileBrowser"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "bash"
SRC_URI="https://github.com/filebrowser/filebrowser/releases/download/v2.1.0/linux-armv7-filebrowser.tar.gz \
         file://fileBrowser.service"

S = "${WORKDIR}"

SRC_URI[md5sum] = "02ff427564c9002b70a02bab04887f31"
SRC_URI[sha256sum] = "87451de51f2b230a095225c450a846da48c4f7589c2524cb8b4693a215ad3dff"

inherit systemd

do_install_append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/fileBrowser.service ${D}${systemd_system_unitdir}
}

do_install(){
    install -d ${D}/usr/bin
    install -m 0755 ${S}/filebrowser ${D}/usr/bin
}

FILES_${PN} += "/usr/bin/filebrowser"
FILES_${PN} += "${systemd_system_unitdir}/fileBrowser.service"

