LICENSE = "LGPL"
DESCRIPTION = "A library to make creating GObjects easier - native"
HOMEPAGE = "http://www.5z.com/jirka/gob.html"


require gob2_${PV}.bb
DEPENDS = "bison-native flex-native glib-2.0-native"
inherit native


SRC_URI[md5sum] = "f8721af6f4e90ff48bd7cb4c96a5a94c"
SRC_URI[sha256sum] = "c2977b18d1166c62e3f04373feefc0e2af704da3cb98e32612be4a55fd77a3f9"


