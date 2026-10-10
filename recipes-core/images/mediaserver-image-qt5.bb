include recipes-core/images/core-image-base.bb

inherit mediaserver-image-common
inherit mediaserver-image-hdmi

# The profile flag is intentionally consumed only by this validation. The
# actual HDMI_* values remain build/rpi-config settings.
python __anonymous() {
    if d.getVar("MEDIASERVER_QT5_HDMI_PROFILE") != "1":
        bb.fatal(
            "%s requires the Qt5 HDMI profile. "
            "Build it with: bitbake -R "
            "\"$PWD/sources/meta-mediaserver/conf/yocto_conf/qt5-hdmi.conf\" "
            "mediaserver-image-qt5" % d.getVar("PN")
        )
}

SUMMARY = "Media Server with Qt5"
LICENSE = "MIT"

IMAGE_INSTALL:append = " \
    qtbase \
    qtbase-mkspecs \
    qtbase-plugins \
    qtbase-tools \
    quetzalcoatl \
    mediaserver-startup \
    mediaserver \
"

IMAGE_FEATURES += " splash"
IMAGE_INSTALL:append = " psplash"

SPLASH = "psplash-mediaserver"
