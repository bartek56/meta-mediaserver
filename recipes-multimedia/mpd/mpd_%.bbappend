SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/mpd:"
SRC_URI += " \
    file://mpd.conf \
    file://mpd.conf.rpi3 \
    file://mpd.conf.rpi4 \
    file://mpd.conf.rpi0-2w \
    file://mpd-output-configurator.py \
"

MPD_CONFIG = "mpd.conf"
MPD_CONFIG:raspberrypi3 = "mpd.conf.rpi3"
MPD_CONFIG:raspberrypi4 = "mpd.conf.rpi4"
MPD_CONFIG:raspberrypi0-2w-64 = "mpd.conf.rpi0-2w"

PACKAGECONFIG += "aac" 
PACKAGECONFIG += "alsa" 
PACKAGECONFIG += "ao" 
PACKAGECONFIG += "audiofile" 
PACKAGECONFIG += "bzip2" 
PACKAGECONFIG += "daemon" 
PACKAGECONFIG += "ffmpeg" 
PACKAGECONFIG += "flac" 
PACKAGECONFIG += "fluidsynth" 
PACKAGECONFIG += "httpd" 
PACKAGECONFIG += "id3tag" 
PACKAGECONFIG += "libsamplerate" 
PACKAGECONFIG += "mpg123" 
PACKAGECONFIG += "smb" 
PACKAGECONFIG += "sndfile" 
PACKAGECONFIG += "upnp" 
PACKAGECONFIG += "zlib" 
PACKAGECONFIG += "fifo" 

RDEPENDS:${PN} += "python3-core python3-dbus python3-pygobject avahi-daemon"

do_install:append() {
    install -d ${D}/etc
    install -m 0755 ${UNPACKDIR}/${MPD_CONFIG} ${D}/etc/mpd.conf
    install -m 0755 ${UNPACKDIR}/mpd-output-configurator.py ${D}${bindir}

    if [ -f ${D}${systemd_system_unitdir}/mpd.service ]; then
        sed -i '/^ExecStart=/i ExecStartPre=${bindir}/mpd-output-configurator.py' \
            ${D}${systemd_system_unitdir}/mpd.service
        sed -i '/^After=/s/$/ avahi-daemon.service network-online.target/' \
            ${D}${systemd_system_unitdir}/mpd.service
        sed -i '/^Description=/a Wants=avahi-daemon.service' \
            ${D}${systemd_system_unitdir}/mpd.service
    fi

    install -d ${D}/etc/mediaserver
    ln -sf /etc/mpd.conf ${D}/etc/mediaserver/mpd.conf

}

FILES:${PN} += "etc/mpd.conf"
FILES:${PN} += "${bindir}/mpd-output-configurator.py"
CONFFILES:${PN} += "${sysconfdir}/mpd.conf"
