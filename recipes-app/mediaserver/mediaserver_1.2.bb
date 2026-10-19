SUMMARY = "MediaServer Qt6 GUI app"
SECTION = "apps"
LICENSE = "CLOSED"
DEPENDS += "qtbase qtdeclarative qtdeclarative-native"
RDEPENDS:${PN} = "bash alarm ntfs-3g qtbase qtdeclarative qtdeclarative-qmlplugins qtvirtualkeyboard"

SRCREV = "${AUTOREV}"

SRC_URI = "git://github.com/bartek56/MediaServer;branch=qt6;protocol=https \
          file://fstab_manager.sh \
          file://screensaver.conf \
          file://start.service \
          file://alarm_gui.service \
          file://serviceHelper.sh \
          file://0001-cmake-make-unit-tests-optional.patch \
"

inherit qt6-cmake systemd

EXTRA_OECMAKE += "-DBUILD_TESTING=OFF"

SYSTEMD_SERVICE:${PN} = "start.service alarm_gui.service"

do_compile() {
    cmake_runcmake_build --target MediaServerApp
    cmake_runcmake_build --target Alarm
}

do_install() {
    install -d ${D}/opt
    install -m 0755 ${B}/MediaServerApp/MediaServerApp ${D}/opt/MediaServerApp
    install -m 0755 ${B}/Alarm/Alarm ${D}/opt/AlarmApp

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/start.service ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/alarm_gui.service ${D}${systemd_system_unitdir}

    install -m 0755 ${UNPACKDIR}/fstab_manager.sh ${D}/opt
    install -m 0755 ${UNPACKDIR}/serviceHelper.sh ${D}/opt

    install -d ${D}${sysconfdir}/mediaserver
    install -m 0755 ${UNPACKDIR}/screensaver.conf ${D}${sysconfdir}/mediaserver
}

FILES:${PN} += " \
    /opt/MediaServerApp \
    /opt/AlarmApp \
    /opt/fstab_manager.sh \
    /opt/serviceHelper.sh \
    ${sysconfdir}/mediaserver/screensaver.conf \
    ${systemd_system_unitdir}/start.service \
    ${systemd_system_unitdir}/alarm_gui.service \
"
