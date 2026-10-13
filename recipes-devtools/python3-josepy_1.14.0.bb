SUMMARY = "josepy"
HOMEPAGE = "https://pypi.org/project/josepy"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=d2c2a5517cd7fd190a1aa6dfa23abb7a"
RDEPENDS:${PN} += " python3 bash"
SRC_URI = "git://github.com/certbot/josepy.git;protocol=https;tag=v1.14.0;nobranch=1"
SRCREV = "a6861675bc943026e8c0d5c550e17eba23289547"

inherit python3-dir

do_compile() {
    echo "It's not needed"
}

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/josepy
    cp -r ${S}/src/josepy/* ${D}${PYTHON_SITEPACKAGES_DIR}/josepy
}

FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/josepy/*"
