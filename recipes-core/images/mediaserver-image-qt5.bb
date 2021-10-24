include recipes-core/images/mediaserver-image-base.bb

inherit sdcard_image-rpi

SUMMARY = "Media Server with Qt5"
LICENSE = "MIT"

#gmpc

QT = " \
    qtbase \
    qtbase-mkspecs \
    qtbase-plugins \
    qtbase-tools \
    qt3d \
    qtconnectivity \
    qtquickcontrols \
    qtquickcontrols2 \
    qtdeclarative \
    qtgraphicaleffects \
    qtmultimedia \
    qtvirtualkeyboard \
    qtx11extras \
    qtwebchannel \
    qtcharts \
"


IMAGE_INSTALL_append += " \
    ${QT} \
    mediaserver \
    mediaserver-startup \
"

IMAGE_FEATURES += " splash"

SPLASH = "psplash-mediaserver"

