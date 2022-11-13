SUMMARY = "libmediainfo - require for qnapi"
LICENSE = "GPL"
LIC_FILES_CHKSUM = "file://${WORKDIR}/MediaInfo_DLL_GNU_FromSource/MediaInfoLib/LICENSE;md5=8f93c85175cbc94ea160ad08cc157822"
SRC_URI = "https://mediaarea.net/download/binary/libmediainfo0/${PV}/MediaInfo_DLL_${PV}_GNU_FromSource.tar.xz"

DEPENDS += " zlib curl"

SRC_URI[md5sum] = "47e7541c4241f8e7a4991e83c1c25f03"
SRC_URI[sha256sum] = "cf30ba53ed19a40f342c77ea64e5fc9907d784de666b50f2dbc485550557d53d"

inherit cmake pkgconfig


S = "${WORKDIR}/MediaInfo_DLL_GNU_FromSource/MediaInfoLib/Project/CMake"

do_configure:prepend() {
    find ${WORKDIR}/MediaInfo_DLL_GNU_FromSource/MediaInfoLib/Project/CMake -name CMakeLists.txt | xargs sed -i 's~option(BUILD_ZENLIB "Build bundled ZenLib" OFF)~option(BUILD_ZENLIB "Build bundled ZenLib" ON)~g'
}
