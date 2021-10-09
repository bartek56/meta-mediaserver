FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += "file://vimrc"

do_install_append(){
    install -d ${D}/home/root
    install -m 0700 ${WORKDIR}/vimrc ${D}/home/root/.vimrc
}

FILES_${PN} += "/home/root/.vimrc" 
