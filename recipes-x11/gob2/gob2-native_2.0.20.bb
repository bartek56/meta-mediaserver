LICENSE = "LGPL"
DESCRIPTION = "A library to make creating GObjects easier - native"
HOMEPAGE = "http://www.5z.com/jirka/gob.html"


require gob2_${PV}.bb
DEPENDS = "bison-native flex-native glib-2.0-native"
inherit native

SRC_URI[md5sum] = "1732775cf9ae57f19e3e92bb0b458019"
SRC_URI[sha256sum] = "d1d727aa860f1fff7b84ef242acd88b89aa93a52e220e254eafb6198ae8dab54"


