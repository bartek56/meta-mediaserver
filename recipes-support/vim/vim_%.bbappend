FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://vimrc"

do_install:append(){
    install -d ${D}/home/root    
    install -d ${D}/home/root/.vim/tmp/undo
    install -d ${D}/home/root/.vim/tmp/backup
    install -d ${D}/home/root/.vim/tmp/swap
    install -m 0700 ${WORKDIR}/vimrc ${D}/home/root/.vimrc
}
FILES:${PN} += "/home/root/.vim/tmp/undo"
FILES:${PN} += "/home/root/.vim/tmp/backup"
FILES:${PN} += "/home/root/.vim/tmp/swap"
FILES:${PN} += "/home/root/.vimrc" 
