LICENSE = "LGPL"
DESCRIPTION = "A library to make creating GObjects easier"
HOMEPAGE = "http://www.5z.com/jirka/gob.html"
SECTION = "libs"
DEPENDS = "gtk+ bison flex glib-2.0"
SRC_URI = "http://ftp.5z.com/pub/gob/gob2-${PV}.tar.gz"
SRC_URI[md5sum] = "1732775cf9ae57f19e3e92bb0b458019"
SRC_URI[sha256sum] = "d1d727aa860f1fff7b84ef242acd88b89aa93a52e220e254eafb6198ae8dab54"
LIC_FILES_CHKSUM = "file://COPYING;md5=c93c0550bd3173f4504b2cbd8991e50b"

inherit autotools pkgconfig

build_path="${WORKDIR}/build"

do_compile_prepend() {
    find ${build_path} -name Makefile | xargs sed -i 's~-I/usr/include~-I${STAGING_INCDIR}~g'
    find ${build_path} -name Makefile | xargs sed -i 's~-I$(includedir)~-I${STAGING_INCDIR}~g'
}

