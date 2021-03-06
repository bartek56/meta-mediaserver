LICENSE = "LGPL"
DESCRIPTION = "A library to make creating GObjects easier"
HOMEPAGE = "http://www.5z.com/jirka/gob.html"
SECTION = "libs"
DEPENDS = "gtk+ bison flex glib-2.0"
SRC_URI = "http://ftp.5z.com/pub/gob/old/gob2-${PV}.tar.gz"

SRC_URI[md5sum] = "f8721af6f4e90ff48bd7cb4c96a5a94c"
SRC_URI[sha256sum] = "c2977b18d1166c62e3f04373feefc0e2af704da3cb98e32612be4a55fd77a3f9"

LIC_FILES_CHKSUM = "file://COPYING;md5=c93c0550bd3173f4504b2cbd8991e50b"

inherit autotools pkgconfig

# błąd w kodzie źródłowym tej wersji:
# ../../gob2-2.0.14/src/main.c:2040:3: error: format not a string literal and no format arguments [-Werror=format-security]
# 2040 |   out_printf(out,v->initializer);
#      |   ^~~~~~~~~~

build_path="${WORKDIR}/build"

do_compile_prepend() {
    find ${build_path} -name Makefile | xargs sed -i 's~-I/usr/include~-I${STAGING_INCDIR}~g'
    find ${build_path} -name Makefile | xargs sed -i 's~-I$(includedir)~-I${STAGING_INCDIR}~g'
}

