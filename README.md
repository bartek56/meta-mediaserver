# meta-mediaserver
yocto layer for MediaServer project


1. Create directory and download layers

- mkdir yocto_mediaserver
- cd yocto_mediaserver
- git clone -b zeus git://git.yoctoproject.org/poky.git
- git clone -b zeus git://github.com/meta-qt5/meta-qt5.git
- git clone -b zeus git://git.openembedded.org/meta-openembedded
- git clone -b zeus git://github.com/agherzan/meta-raspberrypi.git
- git clone -b zeus git://github.com/bartek56/meta-mediaserver.git


2. Creating main config template

- source poky/oe-init-build-env build-mediaserver

3. Edit configuration files

File local.conf You can override using commend: 
- cd conf
- wget https://github.com/bartek56/LinuxEmbedded/raw/master/yocto/MediaServer/local.conf

add path to layers in bblayers.conf. Template is in link: https://github.com/bartek56/LinuxEmbedded/blob/master/yocto/MediaServer/bblayers.conf

4. Build MediaServer

- bitbake mediaserver-image-qt5

5. Configure MediaServer

- cd /opt
- ./installScriptYocto.sh


Enjoy !!


Issues:
- gmpc_11.8.15.bb -> 54:gmpc-mpddata-model-playlist.c: more info in gmpc_11.8.15.bb file



