LICENSE = "LGPL"
DESCRIPTION = "A library to make creating GObjects easier"
HOMEPAGE = "http://www.5z.com/jirka/gob.html"
SECTION = "libs"
DEPENDS = "gtk+ bison flex glib-2.0"
SRC_URI = "http://ftp.5z.com/pub/gob/old/gob2-${PV}.tar.gz"

SRC_URI[md5sum] = "05fa7384b30ebb2921430b2615d2c2e5"
SRC_URI[sha256sum] = "80b4683af653809970ef237fa45427b203653edf0dd5e3dc8897433e9c29346c"
LIC_FILES_CHKSUM = "file://COPYING;md5=c93c0550bd3173f4504b2cbd8991e50b"

inherit autotools pkgconfig

build_path="${WORKDIR}/build"

do_compile_prepend() {
    find ${build_path} -name Makefile | xargs sed -i 's~-I/usr/include~-I${STAGING_INCDIR}~g'
    find ${build_path} -name Makefile | xargs sed -i 's~-I$(includedir)~-I${STAGING_INCDIR}~g'
}

