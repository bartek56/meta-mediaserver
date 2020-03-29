LICENSE = "MIT"
SECTION = "libs"
LIC_FILES_CHKSUM = "file://COPYING;md5=344895f253c32f38e182dcaf30fe8a35"
SRCREV = "${PV}"

SRC_URI="http://downloads.sourceforge.net/project/enlightenment/imlib2-src/${PV}/${PN}-${PV}.tar.bz2"

SRC_URI[md5sum] = "a0de8524592bbd9f24fcc6cb8352137c"
SRC_URI[sha256sum] = "3f698cd285cbbfc251c1d6405f249b99fafffafa5e0a5ecf0ca7ae49bbc0a272"

DEPENDS = "freetype libpng libxinerama libxt jpeg libx11 libxcb"
EXTRA_OECONF="--with-x"

S = "${WORKDIR}/${PN}-${PV}"

inherit autotools pkgconfig


