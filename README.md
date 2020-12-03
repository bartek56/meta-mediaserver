# meta-mediaserver
yocto layer for MediaServer project

Required:
- Debian GNU/Linux 10 (buster) 4.19.67-2+deb10u2 (2019-11-11)
- min. 150GB disk space


1. Create directory and download layers

- mkdir yocto_mediaserver
- cd yocto_mediaserver
- git clone -b zeus git://git.yoctoproject.org/poky.git
- git clone -b zeus git://github.com/meta-qt5/meta-qt5.git
- git clone -b zeus git://git.openembedded.org/meta-openembedded
- git clone -b zeus git://git.yoctoproject.org/meta-virtualization
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


Ampache config:

1. set password for root user

- mysql -u root
- - SET PASSWORD FOR 'root'@'localhost' = PASSWORD('mypass');
- - FLUSH PRIVILEGES;
- - exit

2. go to localhost website, click Ampache icon

Database Name: ampachedb
MySQL hostname: 127.0.0.1
MySQL port: [empty]
MySQL administrative username: root
MySQL administrative password: mypass
Create Databse: checked
Create Database User: (optional)

next Window:
Database Name: ampachedb
MySQL Hostname: 127.0.0.1
MySQL Port: [empty]
MySQL Username: root
MySQL password: mypass


