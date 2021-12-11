# meta-mediaserver
yocto layer for MediaServer project

Required:.
- Debian 10 (buster) or Ubuntu 18.04
- min. 150GB disk space


1. Create directory and download layers

- mkdir yocto_mediaserver
- cd yocto_mediaserver
- git clone -b hardknott git://git.yoctoproject.org/poky.git
- git clone -b hardknott git://github.com/meta-qt5/meta-qt5.git
- git clone -b hardknott git://git.openembedded.org/meta-openembedded
- git clone -b hardknott git://git.yoctoproject.org/meta-virtualization
- git clone -b hardknott git://github.com/agherzan/meta-raspberrypi.git
- git clone -b hardknott git://github.com/bartek56/meta-mediaserver.git


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

without GUI
- bitbake mediaserver-image-base

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


Issue:
1. Manual config pulseaudio access for bluez5 dbus:

  <policy group="pulse">
    <allow send_destination="org.bluez"/>
  </policy>


