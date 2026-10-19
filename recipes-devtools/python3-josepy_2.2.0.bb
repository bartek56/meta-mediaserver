SUMMARY = "josepy"
HOMEPAGE = "https://pypi.org/project/josepy"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=d2c2a5517cd7fd190a1aa6dfa23abb7a"
RDEPENDS:${PN} += " python3 bash"
SRC_URI = "git://github.com/certbot/josepy.git;protocol=https;tag=v${PV};nobranch=1"
SRCREV = "e6af8263cfdec9e3936e62cdc64478deda13f05e"

inherit python3-dir

do_compile() {
    echo "It's not needed"
}

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/josepy
    cp -r ${S}/src/josepy/* ${D}${PYTHON_SITEPACKAGES_DIR}/josepy
}

FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/josepy/*"
