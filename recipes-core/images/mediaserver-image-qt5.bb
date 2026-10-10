include recipes-core/images/core-image-base.bb

inherit mediaserver-image-common
inherit mediaserver-image-hdmi

# The profile flag is intentionally consumed only by this validation. The
# actual HDMI_* values remain build/rpi-config settings. This check belongs to
# a task, not an anonymous parse function: BitBake parses all image recipes
# even when the requested target is mediaserver-image-base.
python do_rootfs:prepend() {
    if d.getVar("MEDIASERVER_QT5_HDMI_PROFILE") != "1":
        bb.fatal(
            "%s requires the Qt5 HDMI profile. "
            "Build it with: bitbake -R "
            "\"conf/machine/qt5-hdmi.conf\" "
            "mediaserver-image-qt5 "
            "or mc:rpi4-qt5:mediaserver-image-qt5" % d.getVar("PN")
        )
}

do_rootfs[vardeps] += "MEDIASERVER_QT5_HDMI_PROFILE"

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
