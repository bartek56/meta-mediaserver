# meta-mediaserver
yocto layer for MediaServer project

Support machine: Raspberry Pi Zero 2w, Raspberry Pi 3b, Raspberry Pi 4

Required:.
- Ubuntu 22.04.1 LTS or Docker
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

- mkdir -p yocto_mediaserver/sources
- cd yocto_mediaserver/sources
- git clone -b kirkstone https://git.yoctoproject.org/poky
- git clone -b kirkstone https://github.com/meta-qt5/meta-qt5
- git clone -b kirkstone https://git.openembedded.org/meta-openembedded
- git clone -b kirkstone https://git.yoctoproject.org/meta-virtualization
- git clone -b kirkstone https://github.com/agherzan/meta-raspberrypi
- git clone -b kirkstone https://github.com/bartek56/meta-mediaserver


2. Generate and run Docker image

docker build -t yocto-ubuntu-22.04 meta-mediaserver/conf/docker/
ln -s sources/meta-mediaserver/conf/docker/docker-compose.yml docker-compose.yml
docker compose run --rm yocto


3. Edit configuration files

- cp ../sources/meta-mediaserver/conf/yocto_conf/bblayers.conf.sample conf/bblayers.conf

File local.conf depends on target
for target with Qt5 Gui
- cp ../sources/meta-mediaserver/conf/yocto_conf/local.conf.qt5.sample conf/local.conf

for target without Qt5 Gui
- cp ../sources/meta-mediaserver/conf/yocto_conf/local.conf.base.sample conf/local.conf


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
