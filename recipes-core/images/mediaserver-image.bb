# Pulled from a mix of different images:
include recipes-core/images/rpi-basic-image.bb
# This image is a little more full featured, and includes wifi
# support, provided you have a raspberrypi3
inherit sdcard_image-rpi
SUMMARY = "The minimal image that can run Qt5 applications"
LICENSE = "MIT"

# PHP
# PYTHON module
# ntfs-3G
# ympd
# w_scan
# bmon
# transmission
# gmpc
# feh
# gqview
# midori
# python-mutagen

NETWORK = " \
    apache2 \
    dhcpcd \
    bluez5 \
    crda\
    iw \
    rsync \
    vsftpd \ 
    wget \
    wpan-tools \
    screen \
    iptables \
    wpa-supplicant \
    rsync \
    iftop \ 
    php \
"

QT = " \
    qtbase \
    qtbase-dev \
    qtbase-mkspecs \
    qtbase-plugins \
    qtbase-tools \
    qt3d \
    qt3d-dev \
    qt3d-mkspecs \
    qtcharts \
    qtcharts-dev \
    qtcharts-mkspecs \
    qtconnectivity-dev \
    qtconnectivity-mkspecs \
    qtquickcontrols \
    qtquickcontrols2 \
    qtquickcontrols2-dev \
    qtquickcontrols2-mkspecs \
    qtdeclarative \
    qtdeclarative-dev \
    qtdeclarative-mkspecs \
    qtgraphicaleffects \
    qtgraphicaleffects-dev \
    qtmultimedia-dev \
    qtmultimedia-mkspecs \
    qtmultimedia-examples \
    qtvirtualkeyboard-dev \
    qtvirtualkeyboard-mkspecs \
    qtwebengine-dev \
    qtwebengine-examples \
    qtwebchannel-dev \
    libconnman-qt5 \
    qtx11extras \
"

X11 = " \
"

MY_FEATURES = " \
    linux-firmware-bcm43430 \
    bluez5 \
    i2c-tools \
    python-smbus \
    bridge-utils \
    hostapd \
    screen \
    wget \
    at \
    minicom \
    mc \
"

TEXT_EDITOR = " \
    nano \
    vim \
"

AUDIO = " \
    alsa-utils \
    pulseaudio \
    mpg123 \
    mplayer-common \
    sox \
    mpd \
    mpc \
    mpv \
    espeak \
"

MULTIMEDIA = " \
    ffmpeg \
    minidlna \
    tvheadend \
    vlc \
    omxplayer \
    bluez-alsa \
"


DISTRO_FEATURES_append += " bluez5 bluetooth wifi systemd "

MACHINE_FEATURES = "bluetooth wifi"

IMAGE_INSTALL_append += " \
    ${QT} \
    ${X11} \
    ${MY_FEATURES} \
    ${AUDIO} \
    ${MULTIMEDIA} \
    ${TEXT_EDITOR} \
    ${NETWORK} \
    git \
    mediaserver \
    bash \
    xfmpc \
    gnome-bluetooth \
    transmission \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"

SPLASH = "psplash-raspberrypi"

IMAGE_FSTYPES ?= "tar.bz2 ext3 rpi-sdimg"

SERIAL_CONSOLE = "115200 ttyAMA0"

IMAGE_FEATURES += " splash package-management x11-base x11-sato ssh-server-dropbear hwcodecs"


TOOLCHAIN_HOST_TASK_append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK_remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"


