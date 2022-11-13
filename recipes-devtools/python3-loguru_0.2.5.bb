SUMMARY = "loguru"
HOMEPAGE = "https://pypi.org/project/loguru/"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://README.rst;md5=77f62fe2f7334dcf0818ae7e5b40eefa"
RDEPENDS:${PN} += " python3-colorama python3-ansimarkup python3-better-exceptions-fork"
SRC_URI[sha256sum] = "68297d9f23064c2f4764bb5d0c5c767f3ed7f9fc1218244841878f5fc7c94add"

PYPI_PACKAGE = "loguru"

inherit pypi setuptools3

