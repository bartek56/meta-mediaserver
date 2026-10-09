SUMMARY = "Textual framework for terminal user interfaces"
HOMEPAGE = "https://github.com/Textualize/textual"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=efa34cbda5817e1e7c540c6cff8f033d"

SRC_URI[sha256sum] = "3a01be0b583f2bce38b8e9786b75ed33dddc816bba502d8e7a9ca3ca2ead3957"

PYPI_PACKAGE = "textual"
inherit pypi python_poetry_core

RDEPENDS:${PN} += " \
    python3-markdown-it-py \
    python3-mdit-py-plugins \
    python3-linkify-it-py \
    python3-platformdirs \
    python3-rich \
    python3-typing-extensions \
"

