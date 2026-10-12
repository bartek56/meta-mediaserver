include recipes-core/images/core-image-base.bb

inherit mediaserver-image-common

SUMMARY = "Media Server without GUI"
LICENSE = "MIT"

IMAGE_INSTALL:append = " configscript transmission-web"

