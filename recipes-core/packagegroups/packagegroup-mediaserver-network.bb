SUMMARY = "MediaServer network packages"
DESCRIPTION = "Network services and tools used by the MediaServer images."
LICENSE = "MIT"

inherit packagegroup

RDEPENDS:${PN} = " \
    dhcpcd \
    iw \
    rsync \
    wget \
    python3-wakeonlan \
    wpan-tools \
    iptables \
    wpa-supplicant \
    iftop \
    vsftpd \
    samba \
    filebrowser \
    speedtest \
    mediaserver-web \
    transmission \
    transmission-web \
    openssh-sftp \
    openssh-sftp-server \
"
