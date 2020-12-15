SUMMARY = "Replacement recipe"

do_install_append() {
        mv ${D}/usr/share/X11/xorg.conf.d/10-evdev.conf ${D}/usr/share/X11/xorg.conf.d/45-evdev.conf
}

#FILES_${PN} += "${systemd_system_unitdir}/pcmanfm.service"

