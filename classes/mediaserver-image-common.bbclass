# Common image policy for the standard and Qt5 MediaServer images.
#
# The minimal image intentionally does not inherit this class: the package set
# below is the existing product "base" image and would make a headless audio
# endpoint larger than necessary.
inherit sdcard_image-rpi

# Keep the boot partition size used by the existing product images.  This is
# image layout, not Raspberry Pi machine configuration.
BOOT_SPACE = "131072"
IMAGE_FSTYPES ?= "tar.bz2 ext3 rpi-sdimg"

NETWORK = " \
    dhcpcd \
    iw \
    rsync \
    wget \
    python3-wakeonlan \
    wpan-tools \
    screen \
    iptables \
    wpa-supplicant \
    iftop \
    vsftpd \
    samba \
    filebrowser \
    speedtest \
    youtubedl-web \
    mediaserver-web \
    transmission \
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
    system-configurator \
    configscript \
    localedef \
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
    alarm \
"

# These are product image requirements shared by the old base image and the
# old Qt5 image (Qt itself is added only by mediaserver-image-qt5.bb).
DISTRO_FEATURES:append = " bluez5 bluetooth wifi libpam pam"
DISTRO_FEATURES += "pam libpam"

IMAGE_INSTALL:append = " \
    ${TOOLS} \
    ${AUDIO} \
    ${MULTIMEDIA} \
    ${TEXT_EDITOR} \
    ${NETWORK} \
    apache2 \
    php-modphp \
    docker \
    snapcast-client \
    snapcast-server \
    danfoss-thermostat \
    kernel-modules \
"

IMAGE_FEATURES += " package-management ssh-server-openssh hwcodecs allow-empty-password empty-root-password allow-root-login"

GLIBC_GENERATE_LOCALES = "pl_PL.UTF-8 en_US.UTF-8"
IMAGE_LINGUAS = "pl-pl en-us en-gb"

TOOLCHAIN_HOST_TASK:append = " nativesdk-intltool nativesdk-glib-2.0"
TOOLCHAIN_HOST_TASK:remove_task-populate-sdk-ext = " nativesdk-intltool nativesdk-glib-2.0"

QB_MEM = '${@bb.utils.contains("DISTRO_FEATURES", "opengl", "-m 512", "-m 256", d)}'
QB_MEM_qemumips = "-m 256"
