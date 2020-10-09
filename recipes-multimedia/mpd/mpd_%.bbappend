SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/mpd:"
SRC_URI += "file://mpd.conf"

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

do_install_append() {
    install -d ${D}/etc
    install -m 0755 ${WORKDIR}/mpd.conf ${D}/etc
}

FILES_${PN} += "etc/mpd.conf"

