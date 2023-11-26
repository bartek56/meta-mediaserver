SUMMARY = "flask-session"
HOMEPAGE = "https://pypi.org/project/Flask-Session/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.rst;md5=b9028d4d777914a850bb142f24398125"

SRC_URI = "https://github.com/pallets-eco/flask-session/releases/download/${PV}/Flask-Session-${PV}.tar.gz"
SRC_URI[sha256sum] = "190875e6aebf2953c6803d42379ef3b934bc209ef8ef006f97aecb08f5aaeb86"

RDEPENDS:${PN} += "python3-cachelib"

inherit python3native

S = "${WORKDIR}/Flask-Session-${PV}"

do_compile() {
    :
}

do_install() {
    install -d ${D}${PYTHON_SITEPACKAGES_DIR}/flask_session
    install -m 0644 ${S}/src/flask_session/sessions.py ${D}${PYTHON_SITEPACKAGES_DIR}/flask_session/
    install -m 0644 ${S}/src/flask_session/__init__.py ${D}${PYTHON_SITEPACKAGES_DIR}/flask_session/
}

FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/flask_session/sessions.py"
FILES:${PN} += "${PYTHON_SITEPACKAGES_DIR}/flask_session/__init__.py"

