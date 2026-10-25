SUMMARY = "MediaServer multimedia packages"
DESCRIPTION = "Multimedia services used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    jellyfin \
    snapcast-client \
    snapcast-server \
    snapcast-bt \
    snapweb \
    minidlna \
    mpd \
    mpc \
    ympd \
    ytcast-open \
"
