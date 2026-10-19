SUMMARY = "Jellyfin container service configuration"
DESCRIPTION = "Systemd service and runtime configuration for Jellyfin running in Docker"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=87758e98f3216b4b339b52592c0d8946"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI = " \
    file://LICENSE \
    file://jellyfin.conf \
    file://jellyfin.service \
"

S = "${UNPACKDIR}"
JELLYFIN_IMAGE = "jellyfin/jellyfin:${PV}"

inherit allarch systemd

RDEPENDS:${PN} = "docker"

SYSTEMD_PACKAGES = "${PN}"
SYSTEMD_SERVICE:${PN} = "jellyfin.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install() {
    install -d ${D}${sysconfdir}/jellyfin/config
    install -d ${D}${sysconfdir}/jellyfin/cache

    install -d ${D}${sysconfdir}/mediaserver
    install -m 0644 ${S}/jellyfin.conf \
        ${D}${sysconfdir}/mediaserver/jellyfin.conf

    install -d ${D}${systemd_system_unitdir}
    sed -e 's|@DOCKER@|${bindir}/docker|g' \
        -e 's|@JELLYFIN_IMAGE@|${JELLYFIN_IMAGE}|g' \
        ${S}/jellyfin.service > ${D}${systemd_system_unitdir}/jellyfin.service
    chmod 0644 ${D}${systemd_system_unitdir}/jellyfin.service
}

CONFFILES:${PN} += "${sysconfdir}/mediaserver/jellyfin.conf"

FILES:${PN} += " \
    ${sysconfdir}/jellyfin/config \
    ${sysconfdir}/jellyfin/cache \
    ${sysconfdir}/mediaserver/jellyfin.conf \
    ${systemd_system_unitdir}/jellyfin.service \
"
