SUMMARY = "Replacement recipe"
FILESEXTRAPATHS:prepend := "${THISDIR}/mpd:"
SRC_URI += " \
    file://mpd.conf \
    file://mpd.conf.rpi3 \
    file://mpd.conf.rpi4 \
    file://mpd.conf.rpi0-2w \
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

do_install:append() {
    install -d ${D}/etc
    install -m 0755 ${UNPACKDIR}/${MPD_CONFIG} ${D}/etc/mpd.conf

    install -d ${D}/etc/mediaserver
    ln -sf /etc/mpd.conf ${D}/etc/mediaserver/mpd.conf

}

FILES:${PN} += "etc/mpd.conf"
