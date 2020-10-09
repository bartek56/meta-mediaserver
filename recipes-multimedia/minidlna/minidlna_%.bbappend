SUMMARY = "Replacement recipe"
FILESEXTRAPATHS_prepend := "${THISDIR}/minidlna:"
SRC_URI += "file://minidlna.conf \
            file://minidlna.service \
            file://IMG_20190816_184930.jpg \
            file://IMG_20190816_194040.jpg \
            file://IMG_20190922_113034.jpg \
            file://IMG_20190922_171239.jpg \
            file://Kings_Of_Leon_-_Sex_on_Fire.mp3 \
            file://Myslovitz_-_Nienawisc.mp3 \
            file://Sam_Smith_-_Money_On_My_Mind.mp3 \
            file://VID_20190813_184721.mp4 "

inherit systemd

SYSTEMD_SERVICE_${PN} = "minidlna.service"
SYSTEMD_PACKAGES = "${PN}" 

do_install_append() {
    install -m 0755 ${WORKDIR}/minidlna.conf ${D}/etc
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/minidlna.service ${D}${systemd_system_unitdir}

    install -d ${D}/home/Videos

    install -d ${D}/home/Pictures
    cp ${WORKDIR}/IMG_20190816_184930.jpg ${D}/home/Pictures/
    cp ${WORKDIR}/IMG_20190816_194040.jpg ${D}/home/Pictures/
    cp ${WORKDIR}/IMG_20190922_113034.jpg ${D}/home/Pictures/
    cp ${WORKDIR}/IMG_20190922_171239.jpg ${D}/home/Pictures/

    install -d ${D}/home/Music
    cp ${WORKDIR}/Kings_Of_Leon_-_Sex_on_Fire.mp3 ${D}/home/Music/
    cp ${WORKDIR}/Myslovitz_-_Nienawisc.mp3 ${D}/home/Music/
    cp ${WORKDIR}/Sam_Smith_-_Money_On_My_Mind.mp3 ${D}/home/Music/    

    install -d ${D}/home/Videos
    cp "${WORKDIR}/VID_20190813_184721.mp4" ${D}/home/Videos/
}

FILES_${PN} += "${systemd_system_unitdir}/minidlna.service"
FILES_${PN} += "home/Music/*"
FILES_${PN} += "home/Videos/*"
FILES_${PN} += "home/Pictures/*"

