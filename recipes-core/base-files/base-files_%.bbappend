do_install_append () {
    echo "192.168.1.10 opkg-server" >> ${D}${sysconfdir}/hosts
}

