# Pulled from a mix of different images:
include recipes-core/images/rpi-basic-image.bb
# This image is a little more full featured, and includes wifi
# support, provided you have a raspberrypi3
inherit sdcard_image-rpi
SUMMARY = "The minimal image that can run Qt5 applications"
LICENSE = "MIT"

# epiphany

# w_scan

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
 xf86-input-evdev  \
 xf86-input-libinput \
 xf86-input-mouse \
 xf86-input-keyboard \
 xf86-video-fbdev \
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
    qtx11extras \
"

python = " \
    python-youtubedl \
    python-mutagen \
"

MY_FEATURES = " \
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
    pulseaudio-server \
    pulseaudio-misc \
    pulseaudio-module-dbus-protocol \
    pulseaudio-module-native-protocol-tcp \
    pulseaudio-module-esound-protocol-tcp \
    pulseaudio-module-zeroconf-publish \
    pulseaudio-module-console-kit \
    pulseaudio-module-cli \
    pulseaudio \
    alsa-utils \
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
    qnapi \
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
    git \
    mediaserver \
    bash \
    transmission \
    ristretto \
    vlc \ 
    xfmpc \
    gmpc \
    tzdata \ 
    configscript \
    docker \
    localedef \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"

SPLASH = "psplash-mediaserver"

IMAGE_FSTYPES ?= "tar.bz2 ext3 rpi-sdimg"

IMAGE_FEATURES += " splash package-management x11-base ssh-server-openssh hwcodecs"

GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "en-us en-gb pl-pl"
#LOCALE_UTF8_ONLY="1"

TOOLCHAIN_HOST_TASK_append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK_remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"


