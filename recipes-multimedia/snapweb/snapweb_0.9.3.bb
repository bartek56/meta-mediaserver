SUMMARY = "Snapcast web interface"
DESCRIPTION = "Mobile-friendly web client for Snapcast"
HOMEPAGE = "https://github.com/snapcast/snapweb"
SECTION = "multimedia"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=7702f203b58979ebbc31bfaeb44f219c"

SRC_URI = "git://github.com/snapcast/snapweb.git;branch=develop;protocol=https"
SRCREV = "9acee022e41da4974ad5f001e61f185dbad76917"

# DEPENDS += "nodejs-native"
do_compile() {

}

do_install() {
    install -d ${D}${datadir}/snapserver/snapweb
    cp --no-preserve=ownership --recursive \
        ${S}/. \
        ${D}${datadir}/snapserver/snapweb/
}

FILES:${PN} = "${datadir}/snapserver/snapweb"
