SUMMARY = "josepy"
HOMEPAGE = "https://pypi.org/project/josepy"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=d2c2a5517cd7fd190a1aa6dfa23abb7a"
RDEPENDS:${PN} += " python3 bash"
SRC_URI = "https://github.com/certbot/josepy/archive/refs/tags/v1.14.0.tar.gz"

SRC_URI[sha256sum] = "7d1adcaa68add9bacf4cff03b571f36015edb6bff6458c76f63ed70ae8ac8b62"

S = "${WORKDIR}/josepy-1.14.0"
inherit python3-dir

do_compile() {
    echo "It's not needed"
}

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/josepy
    cp -r ${S}/src/josepy/* ${D}${PYTHON_SITEPACKAGES_DIR}/josepy
}

FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/josepy/*"