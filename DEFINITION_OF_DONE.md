# Definition of Done — Fresh MediaServer Image

## Purpose and scope

This checklist is used to accept a freshly built and deployed MediaServer
image on Raspberry Pi. It covers:

- mediaserver-image-minimal — Snapcast/PulseAudio audio endpoint,
- mediaserver-image-base — server without GUI,
- mediaserver-image-qt5 — base image with Qt5 applications and touchscreen support.

Testing must be performed on a clean SD card/fresh installation, without reusing
data, configuration, or cache from a previous system. A checklist item is
complete only when marked [x], test evidence is attached, and any deviation has
an owner and a target resolution date.

## 1. Image and artifact identification

- [ ] Record the meta-mediaserver commit, Yocto branch, MACHINE, image name, and test date.
- [ ] The image builds without BitBake errors or new, unaccepted QA warnings.
- [ ] The correct *.rpi-sdimg artifact was built and its checksum verified.
- [ ] build/tmp/deploy/images/<machine>/ contains the image manifest, rootfs image, and boot files; the manifest contains the expected packages.
- [ ] The image contains no build-host paths, test data, keys, passwords, or unintended debug files.
- [ ] For the qt5 variant, verify mediaserver, mediaserver-startup, quetzalcoatl, qnapi, and the required Qt5 libraries.
- [ ] For the base variant, verify the multimedia, network, and web services listed in the image manifest.

## 2. Installation and first boot

- [ ] Write the image to the SD card using the approved tool; verify the target device and image checksum before writing.
- [ ] Raspberry Pi boots from a clean card and completes boot without entering emergency mode.
- [ ] systemctl --failed does not report any service that is critical for the image.
- [ ] journalctl -b -p err..alert contains no errors that block operation.
- [ ] Hostname is MediaServer, timezone is Europe/Warsaw, and the clock synchronizes after network access is available.
- [ ] The rootfs partition has the expected size and sufficient free space after first boot; writing to /var, /home, and /tmp works.
- [ ] Restart and complete power-cycle both result in a successful boot without manually starting services.
- [ ] UART/SSH access works according to the product policy; connection is possible after DHCP and after reboot.

## 3. Configuration and security

- [ ] The target Wi-Fi/Ethernet configuration is applied; the image does not use example SSID, password, or other development configuration.
- [ ] Verify that the image contains no secrets stored in plain text in configuration files, logs, shell history, or the SD card image.
- [ ] Default accounts, passwords, SSH keys, and certificates have been changed or removed.
- [ ] The allow-empty-password, empty-root-password, and allow-root-login policy has been explicitly accepted or disabled before release. Leaving these options enabled is a production release blocker.
- [ ] Samba, FTP, File Browser, Transmission, Tvheadend, Apache/PHP, Docker, and SSH are available only on required interfaces and ports.
- [ ] Permissions for /home, /mnt, media directories, configuration, and logs match the user model; there is no unintended guest write access.
- [ ] With the network unavailable, the device still boots and network-dependent services do not block boot.

## 4. Network and system services

- [ ] DHCP works over Ethernet and, for Wi-Fi machines, WLAN; the address remains available after restarting the interface.
- [ ] Bluetooth is detected and an audio device can be paired.
- [ ] systemctl list-unit-files --state=enabled and systemctl is-active confirm the expected service state. In particular, check dhcpcd, wpa_supplicant, pulseaudio, mpd, minidlna, snapserver, snapclient, ympd, filebrowser, transmission-daemon, tvheadend, vsftpd, apache2, youtubedl-web, and the MediaServer applications.
- [ ] Services configured as disabled are intentionally disabled. This includes system-configurator, which requires manual startup when needed.
- [ ] There are no port conflicts; save the output of ss -lntup as test evidence.
- [ ] Correct behavior after network loss/recovery and after restarting each critical service has been verified at least once.

Default verification points, unless changed by image configuration:

| Area | Verification |
| --- | --- |
| Apache / MediaServer Web | HTTP/HTTPS and the page served from /usr/htdocs |
| File Browser | HTTP on port 8090; read and write a test file |
| MiniDLNA | HTTP on port 8200; library discovery by a DLNA client |
| MPD / ympd | MPD on port 6600; ympd interface on the configured port |
| Snapcast | Server stream on port 1704; RPC/HTTP according to configuration |
| Transmission | RPC panel and download of a test file |
| Tvheadend | Web panel and tuner scan/test when hardware is connected |
| Samba | /home share; read and write from an SMB client |
| FTP / SFTP / SSH | Login and file transfer according to the access policy |

## 5. Storage and file applications

- [ ] The /home/Music, /home/Videos, /home/Pictures, /home/Documents, and /home/Downloads directories exist and remain writable after reboot.
- [ ] If the product uses /mnt, mounting and remounting work; a missing device does not cause service restart loops.
- [ ] The same test file can be transferred and read without corruption through SMB, FTP/SFTP, and File Browser.
- [ ] Samba does not expose more data than intended; guest write access is explicitly accepted or disabled.
- [ ] Application state/databases in /var/lib and logs in /var/log are created with the correct ownership and do not fill the rootfs during a short test.
- [ ] Test nextcloud, Ampache, Certbot, sftp-clients, and other recipes not explicitly listed in IMAGE_INSTALL only when the image manifest or product configuration actually includes them.

## 6. Audio, MPD, and multimedia — base and qt5

- [ ] ALSA detects the audio card; aplay -l, amixer, and a playback test complete successfully.
- [ ] PulseAudio runs as a system service, detects the Raspberry Pi output, and the sink name matches the MPD configuration.
- [ ] MPD starts, scans /home/Music, and mpc displays the library.
- [ ] Play an MP3 and another supported codec; audio is audible, without continuous dropouts or errors in the journal.
- [ ] The /tmp/snapmpdfifo FIFO is created during playback and Snapserver sees the MPD stream.
- [ ] Snapcast: the client connects to the correct server, audio is audible, and volume/mute changes work.
- [ ] Bluetooth audio: pairing, sink switching, and playback through bt-snapcast-autoplug work after restarting PulseAudio.
- [ ] MiniDLNA publishes music, photo, and video files; the library refreshes after adding/removing a file.
- [ ] yt-dlp/youtubedl-web: the page loads, a test download completes, metadata and the file are saved to the expected directory, and the task leaves no error in the log.
- [ ] Alarm: configuration, timer, MPD playback, and snooze work after a cold boot.
- [ ] espeak, mpg123, and sox pass a basic playback/processing test when they are part of the product scenario.

## 7. Web and network applications — base and qt5

- [ ] Apache serves MediaServer Web from /usr/htdocs.
- [ ] PHP executes a simple test page, and the PHP–MariaDB connection works when Nextcloud/Ampache is used.
- [ ] File Browser supports login and file transfer within the permitted directory.
- [ ] Transmission starts with the supplied settings.json, the RPC panel works, and a test torrent can be stopped/removed.
- [ ] Tvheadend opens its panel, detects an available tuner, and performs a test scan/reception; when no tuner is available, this is recorded as a limitation rather than treated as a silent success.
- [ ] speedtest starts and returns a result when the network is available.
- [ ] Docker: docker info works, required kernel modules are loaded, and a simple container can be started and stopped.
- [ ] Starting system-configurator manually on tty1 allows supported settings to be read and saved without a traceback.

## 8. GUI, display, and touch — mediaserver-image-qt5 only

- [ ] psplash starts, followed by the Qt5 startup application.
- [ ] The image is visible on the target HDMI/DSI display; resolution and orientation match the Raspberry Pi configuration.
- [ ] Touch works across the entire display, including the edges; touch coordinates align with UI elements.
- [ ] MediaServerApp starts after boot, remains responsive, and can access audio, alarm, and mount-management services.
- [ ] quetzalcoatl controls MPD: library browsing, play/pause, next track, volume, and output selection work.
- [ ] AlarmApp opens from the GUI and reflects the alarm state.
- [ ] QNapi searches for/downloads subtitles for a test file and saves them next to the corresponding media.
- [ ] After reboot, GUI applications start in the expected order; no two processes compete for the display or audio device.

## 9. Resilience and reboot regression

- [ ] Perform at least three cycles: cold boot, reboot, and power-loss/recovery or an equivalent hardware test.
- [ ] After each cycle, services return to the expected state, the MPD library and configuration are intact, and user data remains available.
- [ ] Disconnect and reconnect USB/audio/Bluetooth devices when they are part of the product; the device recovers without manual repair.
- [ ] Verify behavior without Internet access: local playback, LAN access, and boot remain functional.
- [ ] Review logs after the complete test for restart loops, OOM, mount errors, PulseAudio/ALSA errors, and application tracebacks.

## 10. Evidence and release decision

- [ ] Attach the manifest, checksum, systemctl --failed, journalctl -b, ss -lntup, audio test result, network test result, and a photo/short recording of the GUI test for the qt5 variant.
- [ ] Every failed or skipped test has a description, impact, workaround, and issue reference.
- [ ] There is no open blocker involving security, data loss, boot failure, missing access to core services, or audio regression.
- [ ] The product owner has accepted known hardware limitations, such as no Tvheadend test without a tuner or no Bluetooth test without an audio device.
- [ ] Final status is DONE only after sign-off by the tester and release owner.

## Minimal diagnostic commands

The following commands can be used on the device to collect basic evidence:

    cat /etc/os-release
    uname -a
    systemctl --failed
    systemctl list-units --type=service --state=running
    journalctl -b -p err..alert --no-pager
    ss -lntup
    df -h
    free -h
    ip addr
    aplay -l
    amixer scontents
    mpc status
    docker info

Save the results with the image identifier and device MAC address/serial number,
without exposing passwords, keys, or tokens.
