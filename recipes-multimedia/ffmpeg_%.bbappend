PACKAGECONFIG += "avdevice avfilter avcodec avformat swresample swscale postproc avresample \
                   alsa bzlib gpl lzma theora x264 zlib mp3lame \
                   ${@bb.utils.contains('DISTRO_FEATURES', 'x11', 'xv xcb', '', d)}"

