# Pulled from a mix of different images:
include recipes-core/images/rpi-basic-image.bb
# This image is a little more full featured, and includes wifi
# support, provided you have a raspberrypi3
inherit sdcard_image-rpi
SUMMARY = "The minimal image that can run Qt5 applications"
LICENSE = "MIT"

# epiphany

# gmpc
# w_scan
#

NETWORK = " \
    dhcpcd \
    bluez5 \
    crda \
    iw \
    rsync \
    wget \
    wpan-tools \
    screen \
    iptables \
    wpa-supplicant \
    wireless-regdb \
    rsync \
    iftop \ 
    vsftpd \
    samba \
    filebrowser \
"

X11 = " \
 xinit \
 xterm \
 xinput \
 xinput-calibrator \
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

python = " \
    python-youtubedl \
    python-mutagen \
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
    ympd \
    espeak \
"

MULTIMEDIA = " \
    ffmpeg \
    minidlna \
    tvheadend \
    w-scan \
    bluez-alsa \
    ampache \
"


DISTRO_FEATURES_append += " bluez5 bluetooth wifi libpam pam"
DISTRO_FEATURES += "pam libpam"

IMAGE_INSTALL_append = " \
    ${QT} \
    ${X11} \
    ${MY_FEATURES} \
    ${AUDIO} \
    ${MULTIMEDIA} \
    ${TEXT_EDITOR} \
    ${NETWORK} \
    youtubedl \
    php-modphp \
    curl \
    feh \
    git \
    mediaserver \
    bash \
    transmission \
    ristretto \
    vlc \ 
    xfmpc \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"


GPU_MEM_1024 = "256"
HDMI_GROUP = "2" 
HDMI_MODE = "87"
HDMI_FORCE_HOTPLUG = "1"
HDMI_DRIVE = "1"
ENABLE_UART = "1"
DISABLE_OVERSCAN = "1"
ENABLE_SPI_BUS = "1"
DISABLE_SPLASH = "1"
RPI_EXTRA_CONFIG = " \
    dtparam=audio=on \
    dtoverlay=pi3-miniuart-bt \
    hdmi_cvt 800 480 60 6 0 0 0 \
    dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=0,pmax=65535,xohms=400,xmin=2219,xmax=63438,ymin=2913,ymax=64806 \
    "

SPLASH = "psplash-raspberrypi"

IMAGE_FSTYPES ?= "tar.bz2 ext3 rpi-sdimg"

CMDLINE = "root=/dev/mmcblk0p2 rootwait console=tty1 console=ttyAMA0,115200 logo.nologo quiet loglevel=0 vt.global_cursor_default=0"

IMAGE_FEATURES += " splash package-management x11-base ssh-server-openssh hwcodecs"


TOOLCHAIN_HOST_TASK_append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK_remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"


