include recipes-core/images/rpi-basic-image.bb

inherit sdcard_image-rpi

SUMMARY = "Media Server without GUI"
LICENSE = "MIT"


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
    speedtest \
    youtubedl-web \
    mediaserver-web \
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
    ${TOOLS} \
    ${AUDIO} \
    ${MULTIMEDIA} \
    ${TEXT_EDITOR} \
    ${NETWORK} \
    php-modphp \
    docker \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"

IMAGE_FEATURES += " package-management ssh-server-openssh hwcodecs"

GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "en-us en-gb pl-pl"
#LOCALE_UTF8_ONLY="1"

TOOLCHAIN_HOST_TASK_append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK_remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"


