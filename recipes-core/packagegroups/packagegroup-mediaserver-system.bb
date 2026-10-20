SUMMARY = "MediaServer system packages"
DESCRIPTION = "System packages used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    kernel-modules \
    localedef \
    motd-status \
"
