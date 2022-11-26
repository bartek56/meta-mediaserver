PACKAGECONFIG:append = " eglfs accessibility fontconfig gles2 linuxfb tslib"
DEPENDS += "userland"
RDEPENDS:${PN}:append = "userland adwaita-icon-theme"
