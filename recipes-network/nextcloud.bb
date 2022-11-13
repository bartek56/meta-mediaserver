SUMMARY = "Next Cloud"
LICENSE = "CLOSED"

RDEPENDS:${PN} = "php mysql5"
SRC_URI="https://download.nextcloud.com/server/installer/setup-nextcloud.php"

S = "${WORKDIR}"

SRC_URI[sha256sum] = "bc841ef31635f013e2b54e335c405d4a99beab587e42f141697346aa67020459"

do_install(){
    install -d ${D}/usr/htdocs/nextcloud
    install -m 0755 ${S}/setup-nextcloud.php ${D}/usr/htdocs/nextcloud
}

FILES:${PN} += "/usr/htdocs/nextcloud/setup-nextcloud.php"
