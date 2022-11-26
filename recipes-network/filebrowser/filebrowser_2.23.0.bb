SUMMARY = "FileBrowser"
LICENSE = "CLOSED"

RDEPENDS:${PN} += "bash"

# independ from version SRC filename is the same. After update bitbake does not download new version. SSTATE_SKIP resolved problem
# SSTATE_SKIP_CREATION = "1"


SRC_URI:arm="https://github.com/filebrowser/filebrowser/releases/download/v${PV}/linux-armv7-filebrowser.tar.gz \
         file://filebrowser.service"

SRC_URI:aarch64="https://github.com/filebrowser/filebrowser/releases/download/v${PV}/linux-arm64-filebrowser.tar.gz \
         file://filebrowser.service"

S = "${WORKDIR}"

SHA_CHECKSUM:arm = "87451de51f2b230a095225c450a846da48c4f7589c2524cb8b4693a215ad3dff"
SHA_CHECKSUM:aarch64 = "b375cbc2e47ae5159d4cebcae82b2e11070e153efd819cf03d08531572ed46f3"

SRC_URI[sha256sum] = "${SHA_CHECKSUM}"

inherit systemd

SYSTEMD_PACKAGES = "${PN}" 
SYSTEMD_SERVICE:${PN} = "filebrowser.service"

do_install(){
    install -d ${D}/usr/bin
    install -m 0755 ${S}/filebrowser ${D}/usr/bin
}

do_install:append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/filebrowser.service ${D}${systemd_system_unitdir}
}

FILES:${PN} += "/usr/bin/filebrowser"
FILES:${PN} += "${systemd_system_unitdir}/filebrowser.service"
