SUMMARY = "Weather info"
SECTION = "apps"
LICENSE = "CLOSED"

DEPENDS += "qtbase qtquickcontrols2 qttools-native qtxmlpatterns"
RDEPENDS:${PN} += "qtbase qtxmlpatterns qtquickcontrols2"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/bartek56/weather-app;branch=master;protocol=https \
          file://weather.service \
        "

S = "${WORKDIR}/git"

require recipes-qt/qt5/qt5.inc

inherit qmake5 

do_install() {
    install -d ${D}${systemd_unitdir}/system
    install -m 0644 ${WORKDIR}/weather.service ${D}${systemd_unitdir}/system

    install -d ${WORKDIR} ${D}/opt 
    install -m 0644 ${B}/QuickForecast ${D}/opt/weatherapp 
}


FILES:${PN} += "/opt/weatherapp"
FILES:${PN} += "${systemd_system_unitdir}/weather.service"


