PACKAGECONFIG:append = " eglfs accessibility fontconfig gles2 linuxfb tslib dbus"
DEPENDS += "userland"
RDEPENDS:${PN}:append = "userland adwaita-icon-theme"
