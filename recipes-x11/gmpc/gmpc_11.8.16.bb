LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=751419260aa954499f7abaabaa882bbe"
SRCREV = "${PV}"

SRC_URI="http://download.sarine.nl/Programs/gmpc/${PV}/${PN}-${PV}.tar.gz"

SRC_URI[md5sum] = "223aeb000e41697d8fdf54ccedee89d5"
SRC_URI[sha256sum] = "a69414f35396846733632ca9619921d7acda537ffd6d49bd84b444945cb76b2c"


DEPENDS = "glib-2.0 glib-2.0-native gettext-native gettext libmpd libsoup-2.4 sqlite libice libsm libx11 gtk+ intltool-native libunique gob2 gob2-native"
RDEPENDS_gmpc = "glib-2.0 glib-2.0-native gettext-native gettext gtk+ gob2-native gob2"
EXTRA_OECONF="--disable-mmkeys --disable-unique LIBS='-lm' "

S = "${WORKDIR}/${PN}-${PV}"

inherit autotools pkgconfig gettext

FILES_${PN}+="/usr/share/icons/*"


