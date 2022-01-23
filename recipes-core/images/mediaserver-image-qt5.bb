include recipes-core/images/mediaserver-image-base.bb

inherit sdcard_image-rpi

SUMMARY = "Media Server with Qt5"
LICENSE = "MIT"

IMAGE_INSTALL_append += " \
    qtbase \
    qtbase-mkspecs \
    qtbase-plugins \
    qtbase-tools \
    quetzalcoatl \
    weatherapp \
    mediaserver-startup \
    mediaserver \
"

IMAGE_FEATURES += " splash"

SPLASH = "psplash-mediaserver"

