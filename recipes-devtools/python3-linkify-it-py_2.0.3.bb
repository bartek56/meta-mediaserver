SUMMARY = "Linkify URLs in text"
HOMEPAGE = "https://pypi.org/project/linkify-it-py/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=a7aa82f01e7197249f7f2dcb0c0bac97"

SRC_URI[sha256sum] = "68cda27e162e9215c17d786649d1da0021a451bdc436ef9e0fa0ba5234b9b048"

PYPI_PACKAGE = "linkify-it-py"
inherit pypi python_setuptools_build_meta

RDEPENDS:${PN} += "python3-uc-micro-py"

