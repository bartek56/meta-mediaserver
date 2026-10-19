include recipes-core/images/core-image-base.bb

inherit mediaserver-image-common

python do_rootfs:prepend() {
    if d.getVar("MEDIASERVER_QT6_HDMI_PROFILE") != "1":
        bb.fatal(
            "%s requires the Qt6 HDMI profile. "
            "Build it with: bitbake -R "
            "\"conf/machine/qt6-hdmi.conf\" "
            "mediaserver-image-qt6 "
            "or mc:rpi4-qt6:mediaserver-image-qt6" % d.getVar("PN")
        )
}

do_rootfs[vardeps] += "MEDIASERVER_QT6_HDMI_PROFILE"

SUMMARY = "Media Server with Qt6"
LICENSE = "MIT"

require recipes-core/images/mediaserver-image-base.inc

IMAGE_INSTALL:append = " \
    configscript-qt6 \
    qtbase \
    qtbase-plugins \
    qtbase-tools \
    qtdeclarative \
    qtdeclarative-qmlplugins \
    qtvirtualkeyboard \
    qtvirtualkeyboard-qmlplugins \
    quetzalcoatl \
    mediaserver-startup \
    mediaserver \
"

IMAGE_FEATURES += " splash"
IMAGE_INSTALL:append = " psplash"

SPLASH = "psplash-mediaserver"
