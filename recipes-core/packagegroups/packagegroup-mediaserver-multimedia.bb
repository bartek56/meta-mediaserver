SUMMARY = "MediaServer multimedia packages"
DESCRIPTION = "Multimedia services used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    jellyfin \
    snapcast-client \
    snapcast-server \
    minidlna \
    mpd \
    mpc \
    ympd \
"
