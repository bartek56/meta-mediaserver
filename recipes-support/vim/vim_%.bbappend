FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://vimrc"

do_install:append(){
    install -d ${D}/root
    install -d ${D}/root/.vim/tmp/undo
    install -d ${D}/root/.vim/tmp/backup
    install -d ${D}/root/.vim/tmp/swap
    install -m 0700 ${UNPACKDIR}/vimrc ${D}/root/.vimrc
}
FILES:${PN} += "/root/.vim/tmp/undo"
FILES:${PN} += "/root/.vim/tmp/backup"
FILES:${PN} += "/root/.vim/tmp/swap"
FILES:${PN} += "/root/.vimrc"
