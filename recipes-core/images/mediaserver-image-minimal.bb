include recipes-core/images/core-image-base.bb

inherit sdcard_image-rpi

SUMMARY = "Base system without multimedia tools"
LICENSE = "MIT"


NETWORK = " \
    dhcpcd \
    iw \
    rsync \
    wget \
    python3-wakeonlan \
    wpan-tools \
    iptables \
    wpa-supplicant \
    iftop \
    speedtest \
    openssh-sftp \
    openssh-sftp-server \
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
    espeak \
"

DISTRO_FEATURES:append = " bluez5 bluetooth wifi libpam pam"
DISTRO_FEATURES += "pam libpam"

IMAGE_INSTALL:append = " \
    ${TOOLS} \
    ${AUDIO} \
    ${TEXT_EDITOR} \
    ${NETWORK} \
"

# Include modules in rootfs
IMAGE_INSTALL += " \
	kernel-modules \
"

IMAGE_FEATURES += " package-management ssh-server-openssh hwcodecs"

GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "pl-pl en-us en-gb"
#LOCALE_UTF8_ONLY="1"

TOOLCHAIN_HOST_TASK:append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK:remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"
