SUMMARY = "MediaServer GUI app"
SECTION = "examples"
LICENSE = "CLOSED"
DEPENDS += "qtbase qtdeclarative qtquickcontrols2 systemdlib-qt"
RDEPENDS_${PN} = "alarm ntfs-3g qnapi python-wikiquote"
SRC_URI[md5sum] = "5900b09d36848e446e53e19c413ec363"
SRC_URI[sha256sum] = "b828614be6b8be36493e18b7c239d6264dd78e1f4e325301f2d1722cad6eaf5e"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/MediaServer \
          file://fstab_manager.sh \
          file://quotes.py \
          file://screensaver.conf \
          file://start.service \
          file://alarm_gui.service"


S = "${WORKDIR}/git"

require recipes-qt/qt5/qt5.inc

inherit qmake5 

do_compile() {
    oe_runmake sub-MediaServerApp
    oe_runmake sub-Alarm
}

do_install() {
    oe_runmake sub-MediaServerApp-install_subtargets  INSTALL_ROOT=${D}
    oe_runmake sub-Alarm-install_subtargets INSTALL_ROOT=${D}
}

do_install_append() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/start.service ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/alarm_gui.service ${D}${systemd_unitdir}/system

    install -d ${D}/opt
    install -m 0644 ${WORKDIR}/fstab_manager.sh ${D}/opt
    install -m 0644 ${WORKDIR}/quotes.py ${D}/opt

    install -d ${D}/etc/mediaserver
    install -m 0644 ${WORKDIR}/screensaver.conf ${D}${sysconfdir}/mediaserver  
}

FILES_${PN} += "/opt/MediaServerApp"
FILES_${PN} += "/opt/Alarm"
FILES_${PN} += "/opt/fstab_manager.sh"
FILES_${PN} += "/opt/quotes.py"
FILES_${PN} += "${sysconfdir}/mediaserver/screensaver.conf"
FILES_${PN} += "${systemd_system_unitdir}/start.service"
FILES_${PN} += "${systemd_system_unitdir}/alarm_gui.service"

