SUMMARY = "Web assets for MediaServer applications"
DESCRIPTION = "Bootstrap and Clockpicker assets used by the MediaServer web applications."
HOMEPAGE = "https://getbootstrap.com/"
SECTION = "network"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

BOOTSTRAP_VERSION = "5.0.0-beta1"
WEB_ROOT = "${prefix}/htdocs"
YOUTUBEDL_STATIC = "/opt/youtubedl-web/youtubedlWeb/static"

SRC_URI = "git://github.com/twbs/bootstrap.git;protocol=https;branch=master;nobranch=1;name=bootstrap;destsuffix=bootstrap \
           git://github.com/weareoutman/clockpicker.git;protocol=https;branch=gh-pages;name=clockpicker;destsuffix=clockpicker"

SRCREV_bootstrap = "63f3d939eaceeb84dcc77a7392953bcc8c5bc0a3"
SRCREV_clockpicker = "e6ac014b3c167281ac37cf122ab19b6967d8fae4"
SRCREV_FORMAT = "bootstrap_clockpicker"

S = "${UNPACKDIR}"
inherit allarch

do_install() {
    install -d ${D}${WEB_ROOT}
    install -d ${D}${YOUTUBEDL_STATIC}

    cp --no-preserve=ownership --recursive \
        ${UNPACKDIR}/bootstrap/dist \
        ${D}${WEB_ROOT}/bootstrap-5.0.0
    cp --no-preserve=ownership --recursive \
        ${UNPACKDIR}/bootstrap/dist \
        ${D}${YOUTUBEDL_STATIC}/bootstrap-5.0.0
    cp --no-preserve=ownership --recursive \
        ${UNPACKDIR}/clockpicker \
        ${D}${YOUTUBEDL_STATIC}/clockpicker
    rm -rf ${D}${YOUTUBEDL_STATIC}/clockpicker/.git
}

FILES:${PN} = " \
    ${WEB_ROOT}/bootstrap-5.0.0 \
    ${YOUTUBEDL_STATIC}/bootstrap-5.0.0 \
    ${YOUTUBEDL_STATIC}/clockpicker \
"
