SUMMARY = "Dynamic MediaServer login status"
DESCRIPTION = "Keeps /etc/motd updated with CPU, RAM, and mounted disk usage."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=f5a5e90e07df035bc1e7265a8bbb4d35"

SRC_URI = " \
    file://LICENSE \
    file://motd-status.sh \
    file://motd-status-profile.sh \
"

S = "${UNPACKDIR}"

inherit allarch

RDEPENDS:${PN} = " \
    coreutils \
    procps \
    util-linux \
"

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${UNPACKDIR}/motd-status.sh ${D}${bindir}/motd-status

    install -d ${D}${sysconfdir}/profile.d
    sed -e 's,@BINDIR@,${bindir},g' \
        ${UNPACKDIR}/motd-status-profile.sh > ${D}${sysconfdir}/profile.d/motd-status.sh
    chmod 0644 ${D}${sysconfdir}/profile.d/motd-status.sh
}

FILES:${PN} += " \
    ${bindir}/motd-status \
    ${sysconfdir}/profile.d/motd-status.sh \
"
