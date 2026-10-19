FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI:append = " file://docker.cfg"

# Make the modules required by Docker available immediately after boot.
KERNEL_MODULE_AUTOLOAD:append = " overlay br_netfilter veth"
