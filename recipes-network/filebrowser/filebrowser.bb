SUMMARY = "FileBrowser"
LICENSE = "CLOSED"

RDEPENDS_${PN} += "bash"
SRC_URI_arm="https://github.com/filebrowser/filebrowser/releases/download/v2.1.0/linux-armv7-filebrowser.tar.gz \
         file://fileBrowser.service"

SRC_URI_aarch64="https://github.com/filebrowser/filebrowser/releases/download/v2.1.0/linux-arm64-filebrowser.tar.gz \
         file://fileBrowser.service"

S = "${WORKDIR}"

MD5_CHECKSUM_arm = "02ff427564c9002b70a02bab04887f31"
SHA_CHECKSUM_arm = "87451de51f2b230a095225c450a846da48c4f7589c2524cb8b4693a215ad3dff"

#SRC_URI_arm[md5sum] = "02ff427564c9002b70a02bab04887f31"
#SRC_URI_arm[sha256sum] = "87451de51f2b230a095225c450a846da48c4f7589c2524cb8b4693a215ad3dff"

#SRC_URI_aarch64[md5sum] = "9f7f66c6ef5c2025807d1420e6d9015f"
#SRC_URI_aarch64[sha256sum] = "722e5c8ad1964d9e03362ecbec227ac9e829cbdd8b34159ae94559ce223092e4"

MD5_CHECKSUM_aarch64 = "9f7f66c6ef5c2025807d1420e6d9015f"
SHA_CHECKSUM_aarch64 = "722e5c8ad1964d9e03362ecbec227ac9e829cbdd8b34159ae94559ce223092e4"


SRC_URI[md5sum] = "${MD5_CHECKSUM}"
SRC_URI[sha256sum] = "${SHA_CHECKSUM}"

inherit systemd

SYSTEMD_PACKAGES = "${PN}" 
SYSTEMD_SERVICE_${PN} = "fileBrowser.service"


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

