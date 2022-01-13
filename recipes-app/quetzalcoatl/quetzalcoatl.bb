SUMMARY = "MediaServer GUI app"
SECTION = "examples"
LICENSE = "CLOSED"
DEPENDS += "qtbase libmpdclient"
#RDEPENDS_${PN} = "alarm ntfs-3g qnapi python-wikiquote systemdlib-qt"
SRC_URI[md5sum] = "5900b09d36848e446e53e19c413ec363"
SRC_URI[sha256sum] = "b828614be6b8be36493e18b7c239d6264dd78e1f4e325301f2d1722cad6eaf5e"


SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/quetzalcoatl;protocol=https \
           file://mpc_mediaserver.service \
"

S = "${WORKDIR}/git"

inherit cmake_qt5 pkgconfig

do_install(){
    install -d ${D}/opt
	install -m 0755 quetzalcoatl ${D}/opt
    install -d ${D}/usr/share/icons
    cp -r ${S}/app/icons/breeze ${D}/usr/share/icons/


    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/start.service ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/alarm_gui.service ${D}${systemd_unitdir}/system

}

FILES_${PN} += "/opt/quetzalcoatl"
FILES_${PN} += "/usr/share/icons/breeze/*"
FILES_${PN} += "${systemd_system_unitdir}/mpc_mediaserver.service"

