SUMMARY = "MediaServer service packages"
DESCRIPTION = "Core services used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    danfoss-thermostat \
"
