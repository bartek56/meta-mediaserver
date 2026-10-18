PACKAGECONFIG:remove:class-target = " gl"
PACKAGECONFIG:append:class-target = " eglfs accessibility fontconfig gles2 linuxfb tslib dbus"
DEPENDS:append:class-target = " userland"
RDEPENDS:${PN}:append:class-target = " userland adwaita-icon-theme"
