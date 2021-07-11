include recipes-core/images/rpi-basic-image.bb

inherit sdcard_image-rpi

SUMMARY = "Media Server with Qt5"
LICENSE = "MIT"

#pulseaudio-module-esound-protocol-tcp
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

NETWORK = " \
    dhcpcd \
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
    youtubedl-web \
    transmission \
    transmission-web \
"

TOOLS = " \
    bluez5 \
    i2c-tools \
    bridge-utils \
    hostapd \
    screen \
    wget \
    at \
    minicom \
    mc \
    curl \
    git \
    bash \
    tzdata \ 
    configscript \
    localedef \
    dvb-apps \
    dvb-scan \
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
    pulseaudio-module-zeroconf-publish \
    pulseaudio-module-console-kit \
    pulseaudio-module-cli \
    pulseaudio-module-bluez5-device \
    pulseaudio-module-bluez5-discover \
    pulseaudio-module-bluetooth-discover \
    pulseaudio-module-bluetooth-policy \
    pulseaudio-module-loopback \
    pulseaudio \
    mpg123 \
    sox \
    mpd \
    mpc \
    ympd \
    espeak \
"

MULTIMEDIA = " \
    minidlna \
    tvheadend \
    ampache \ 
    nextcloud \
"

DISTRO_FEATURES_append += " bluez5 bluetooth wifi libpam pam"
DISTRO_FEATURES += "pam libpam"

IMAGE_INSTALL_append = " \
    ${QT} \
    ${TOOLS} \
    ${AUDIO} \
    ${MULTIMEDIA} \
    ${TEXT_EDITOR} \
    ${NETWORK} \
    php-modphp \
    docker \
    mediaserver \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"

IMAGE_FEATURES += " splash package-management ssh-server-openssh hwcodecs"

SPLASH = "psplash-mediaserver"

GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "en-us en-gb pl-pl"
#LOCALE_UTF8_ONLY="1"

TOOLCHAIN_HOST_TASK_append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK_remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"


