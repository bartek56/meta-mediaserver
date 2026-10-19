# Yocto configuration map

This map summarizes configuration currently supplied by `meta-mediaserver`.
The recipes and installed files are authoritative if this document and the
tree diverge.

| Area | Recipe or source | Type | Migration |
| --- | --- | --- | --- |
| MPD | `recipes-multimedia/mpd/mpd_%.bbappend`, `mpd.conf*` | Machine-dependent audio configuration | Compare the target audio model and MPD version; prefer the recipe. |
| PulseAudio | `recipes-multimedia/pulseaudio/pulseaudio_%.bbappend` | ALSA rules, service, and PulseAudio policy | Keep common policy only; verify target outputs. |
| Snapcast | `recipes-multimedia/snapcast/snapcast_0.35.0.bb`, `snap*.conf` | Client/server configuration | Compare version, server address, stream names, and sound card. |
| Bluetooth switching | `recipes-multimedia/snapcast-bt/` | PulseAudio event watcher and Snapcast stream switcher | Revalidate Bluetooth source names and Snapcast group layout. |
| YouTube downloader | `recipes-multimedia/youtubedl/` | Timer, playlist configuration, and downloader code | Recreate configuration; migrate downloaded media separately. |
| YouTube DL Web | `recipes-network/youtubedl-web/` | Flask application, Apache proxy, and service | Review web access, sudo policy, and application data manually. |
| Alarm | `recipes-app/alarm/` | MPD alarm script, timers, and settings | Recreate `alarm.ini`; runtime state in `/tmp` is not persistent. |
| MiniDLNA | `recipes-multimedia/minidlna/` | Media server configuration and media roots | Recipe is the source; media is user data. |
| Samba | `recipes-network/samba/` | File-sharing configuration | Review shares, accounts, and permissions. |
| Transmission | `recipes-network/transmission/` | Service configuration and queue | Compare with the new version; migrate queue/data separately. |
| Network | `wpa-supplicant`, `dhcpcd`, and machine configuration | Connectivity and systemd units | Manual review; do not overwrite target identity. |
| SSH | Image features and target `/etc/ssh` | Access and host identity | Do not copy host keys automatically. |
| Systemd units | Most `recipes-*/**/*.bb` | Installed service units | Compare with the image; do not migrate runtime state. |
| MediaServer | `recipes-app/mediaserver*`, `configscript*`, `system-configurator*` | Applications and first-boot configuration | Migrate user input, not generated state. |
| PHP/Apache/FTP | `recipes-network/apache2`, `php`, `vsftpd` | Network services and access data | Manual decision; secrets are excluded. |
| Runtime data | `/var/lib`, `/var/cache`, `/var/log` | Databases, queues, downloads, and logs | Separate data migration. |

Shared image policy is assembled in `classes/mediaserver-image-common.bbclass`.
Package selection and common `IMAGE_INSTALL` settings are defined in
`recipes-core/packagegroups/` and `recipes-core/images/mediaserver-image-base.inc`.
The Qt6/HDMI variant is described by the files under `conf/yocto_conf/` and
the `conf/machine/qt6-hdmi.conf` profile.

Raspberry Pi, HDMI, display, and audio-device settings are machine-specific.
They should not be copied from an old device without checking the selected
`MACHINE`, BSP version, kernel overlays, and physical hardware.
