SUMMARY = "YouTube Music cast receiver for MPD"
DESCRIPTION = "Rust-based YouTube Music cast receiver that exposes a DIAL endpoint and plays streams through MPD."
HOMEPAGE = "https://github.com/mthwJsmith/ytcast-open"
BUGTRACKER = "https://github.com/mthwJsmith/ytcast-open/issues"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://README.md;beginline=168;endline=170;md5=2c0caeec719da2ceeb603cc5d7a82e17"

PV = "0.1.0+git${SRCPV}"
SRCREV = "a8cf53282f101c47525c8c90ca1bbf2b7459eace"
SRCREV_rquickjs = "08e13e08805b71fc4f8d73793af4006ac8be7d4a"
SRCREV_quickjs = "6d46d07d04041b40f4f49eaa7fdebe44c314c699"
SRCREV_FORMAT = "default_rquickjs_quickjs"

FILESEXTRAPATHS:prepend := "${THISDIR}:"

SRC_URI = " \
    git://github.com/mthwJsmith/ytcast-open.git;branch=master;protocol=https \
    git://github.com/DelSkayn/rquickjs.git;branch=master;protocol=https;name=rquickjs;destsuffix=rquickjs;submodules=1 \
    git://github.com/quickjs-ng/quickjs.git;branch=master;protocol=https;name=quickjs;subdir=rquickjs/sys/quickjs \
    file://0001-Disable-Cargo-strip-for-Yocto-packaging.patch \
    file://0002-Pass-OAuth-token-to-SABR-player-requests.patch \
    file://ytcast-open.service \
"

DEPENDS += "protobuf-native"

inherit cargo cargo-update-recipe-crates systemd

require ${BPN}-crates.inc

CARGO_SRC_DIR = ""

do_configure:append() {
    install -m 0644 \
        ${UNPACKDIR}/rquickjs/sys/src/bindings/aarch64-unknown-linux-gnu.rs \
        ${UNPACKDIR}/rquickjs/sys/src/bindings/${RUST_HOST_SYS}.rs
}

SYSTEMD_SERVICE:${PN} = "ytcast-open.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install:append() {
    if [ -e ${D}${bindir}/ytcast-lite ]; then
        mv ${D}${bindir}/ytcast-lite ${D}${bindir}/ytcast-open
    fi

    install -d ${D}${localstatedir}/lib/ytcast-open
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/ytcast-open.service ${D}${systemd_system_unitdir}/ytcast-open.service
}

FILES:${PN} += " \
    ${systemd_system_unitdir}/ytcast-open.service \
    ${localstatedir}/lib/ytcast-open \
"

RDEPENDS:${PN} += "mpd bgutil-pot"
