LICENSE = "CLOSED"

SRC_URI="https://www.gen2vdr.de/wirbel/w_scan/w_scan-${PV}.tar.bz2"

SRC_URI[sha256sum] = "38e0f38a7bf06cff6d6ea01652ad4ee60da2cb0e937360468f936da785b46ffe"

inherit autotools pkgconfig 

S = "${WORKDIR}/w_scan-${PV}"


