# meta-mediaserver
yocto layer for MediaServer project

Support machine: Raspberry Pi Zero 2w, Raspberry Pi 3b, Raspberry Pi 4

Required:.
- Ubuntu 22.04.1 LTS
- min. 150GB disk space

layer support:
- [mediaserver](https://github.com/bartek56/MediaServer)
- [quetzalcoatl](https://github.com/bartek56/quetzalcoatl)
- [qnapi](https://github.com/QNapi/qnapi)
- [filebrowser](https://github.com/filebrowser/filebrowser)
- [ampache](https://github.com/ampache/ampache)
- [transmission](https://github.com/transmission/transmission)
- [mpd](https://github.com/MusicPlayerDaemon/MPD)
- [ympd](https://github.com/notandy/ympd)
- [minidlna](https://github.com/azatoth/minidlna)
- [tvheadend](https://github.com/tvheadend/tvheadend)
- [samba](https://github.com/samba-team/samba)
- [yt_dlt](https://github.com/yt-dlp/yt-dlp)
- [vsftpd](https://github.com/djarosz/vsftpd)


1. Create directory and download layers

- mkdir yocto_mediaserver
- cd yocto_mediaserver
- git clone -b kirkstone git://git.yoctoproject.org/poky.git
- git clone -b kirkstone git://github.com/meta-qt5/meta-qt5.git
- git clone -b kirkstone git://git.openembedded.org/meta-openembedded
- git clone -b kirkstone git://git.yoctoproject.org/meta-virtualization
- git clone -b kirkstone git://github.com/agherzan/meta-raspberrypi.git
- git clone -b kirkstone git://github.com/bartek56/meta-mediaserver.git


2. Creating default config

- source poky/oe-init-build-env build-mediaserver

3. Edit configuration files

File bblayers.conf You can override, but rememebr to change path in this file:
- cp ../meta-mediaserver/conf/bblayers.conf.sample conf/bblayers.conf

File local.conf depends on target
for target with Qt5 Gui
- cp ../meta-mediaserver/conf/local.conf.qt5.sample conf/local.conf

for target without Qt5 Gui
- cp ../meta-mediaserver/conf/local.conf.base.sample conf/local.conf


4. Build MediaServer

with Qt5 GUI:
- bitbake mediaserver-image-qt5

without GUI:
- bitbake mediaserver-image-base

core:
- bitbake mediaserver-image-minimal

5. Configure MediaServer

- cd /opt
- ./installScript.sh


Enjoy !!
