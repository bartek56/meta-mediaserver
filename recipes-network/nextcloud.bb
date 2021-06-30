SUMMARY = "Next Cloud"
LICENSE = "CLOSED"

RDEPENDS_${PN} = "php mysql5"
SRC_URI="https://download.nextcloud.com/server/installer/setup-nextcloud.php"

S = "${WORKDIR}"

SRC_URI[md5sum] = "803ff3dc68fc6d052dc603418da3efa2"
SRC_URI[sha256sum] = "9c8cee9470265e9aa95cda8f038595720bbff08d07b615f5cb4c92275e817c27"

do_install(){
    install -d ${D}/usr/htdocs/nextcloud
    install -m 0755 ${S}/setup-nextcloud.php ${D}/usr/htdocs/nextcloud
}

FILES_${PN} += "/usr/htdocs/nextcloud/setup-nextcloud.php"


