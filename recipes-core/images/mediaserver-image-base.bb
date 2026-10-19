include recipes-core/images/core-image-base.bb

inherit mediaserver-image-common

SUMMARY = "Media Server without GUI"
LICENSE = "MIT"

require recipes-core/images/mediaserver-image-base.inc

IMAGE_INSTALL:append = " configscript"

