SUMMARY = "YouTube Proof-of-Origin Token provider"
DESCRIPTION = "Rust HTTP service that generates YouTube PoTokens for SABR streaming."
HOMEPAGE = "https://github.com/jim60105/bgutil-ytdlp-pot-provider-rs"
BUGTRACKER = "https://github.com/jim60105/bgutil-ytdlp-pot-provider-rs/issues"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=1ebbd3e34237af26da5dc08a4e440464"

PV = "0.8.1+git${SRCPV}"
SRCREV = "1fc504aa17ab817073e86a77f58b4413d6df6933"

DEPENDS += "openssl"

# rusty_v8 derives the prebuilt archive name from TARGET. Yocto's target
# triple is aarch64-poky-linux-gnu, while the upstream archive uses the
# compatible aarch64-unknown-linux-gnu triple.
RUSTY_V8_ARCHIVE_URL = "https://github.com/denoland/rusty_v8/releases/download/v130.0.7/librusty_v8_release_aarch64-unknown-linux-gnu.a.gz"

FILESEXTRAPATHS:prepend := "${THISDIR}:"

SRC_URI = " \
    git://github.com/jim60105/bgutil-ytdlp-pot-provider-rs.git;branch=master;protocol=https \
    file://0001-Disable-Cargo-strip-for-Yocto-packaging.patch \
    file://bgutil-pot.service \
"

inherit cargo cargo-update-recipe-crates pkgconfig systemd

require ${BPN}-crates.inc

CARGO_SRC_DIR = ""

do_compile:prepend() {
    export RUSTY_V8_ARCHIVE="${RUSTY_V8_ARCHIVE_URL}"
    export RUSTY_V8_SRC_BINDING_PATH="${CARGO_HOME}/bitbake/v8-130.0.7/gen/src_binding_release_aarch64-unknown-linux-gnu.rs"
}

SYSTEMD_SERVICE:${PN} = "bgutil-pot.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

do_install:append() {
    install -d ${D}${localstatedir}/lib/bgutil-pot
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/bgutil-pot.service ${D}${systemd_system_unitdir}/bgutil-pot.service
}

FILES:${PN} += " \
    ${systemd_system_unitdir}/bgutil-pot.service \
    ${localstatedir}/lib/bgutil-pot \
"
