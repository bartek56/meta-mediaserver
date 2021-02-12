LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://COPYING;md5=751419260aa954499f7abaabaa882bbe"
SRCREV = "${PV}"

SRC_URI="http://download.sarine.nl/Programs/gmpc/${PV}/${PN}-${PV}.tar.gz \
         file://gmpc.service \
         file://99-calibration.conf "

SRC_URI[md5sum] = "223aeb000e41697d8fdf54ccedee89d5"
SRC_URI[sha256sum] = "a69414f35396846733632ca9619921d7acda537ffd6d49bd84b444945cb76b2c"


DEPENDS = "glib-2.0 gettext-native gettext libmpd libsoup-2.4 sqlite libice libsm libx11 gtk+ intltool-native libunique gob2-native"
RDEPENDS_${PN} = "gtk+ xserver-xorg xinit xterm xinput xinput-calibrator xf86-input-evdev xf86-input-libinput xf86-input-mouse xf86-input-keyboard xf86-video-fbdev"
EXTRA_OECONF="--disable-mmkeys --disable-unique LIBS='-lm' "

S = "${WORKDIR}/${PN}-${PV}"

inherit autotools pkgconfig gettext

build_path="${WORKDIR}/build"

do_install_append() {
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/gmpc.service ${D}${systemd_system_unitdir}
    
    install -d ${D}/usr/share/X11/xorg.conf.d/
    install -m 0755 ${WORKDIR}/99-calibration.conf ${D}/usr/share/X11/xorg.conf.d/
}

FILES_${PN} += "/usr/share/icons/* \
               ${systemd_system_unitdir}/gmpc.service"

FILES_${PN} += "usr/share/X11/xorg.conf.d/99-calibration.conf"

