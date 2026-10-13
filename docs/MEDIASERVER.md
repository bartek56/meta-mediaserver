# MediaServer layer

`meta-mediaserver` is a Yocto layer for building MediaServer images on the
Yocto Project Wrynose release (6.0). The supported Raspberry Pi machines are
`raspberrypi0-2w-64`, `raspberrypi3-64`, and `raspberrypi4-64`.

The layer provides three image profiles:

| Image | Intended role |
| --- | --- |
| `mediaserver-image-minimal` | Headless audio endpoint: Snapcast client and PulseAudio receiver. |
| `mediaserver-image-base` | Full non-GUI MediaServer, including MPD, Snapcast server/client, Bluetooth audio, web services, and network services. |
| `mediaserver-image-qt5` | The base image plus the Qt5 user interface, HDMI/display profile, MediaServer application, and splash screen. |

The image recipes are independent. Qt5 is not installed implicitly in the
base or minimal image.

## Audio architecture

The main audio path is built from MPD, PulseAudio, and Snapcast:

```text
local files / YouTube downloads
              |
             MPD
        /              \
 PulseAudio sink       FIFO: /tmp/snapmpdfifo
        |                         |
 local / Bluetooth output     Snapserver (stream: MPD)
                                      |
                              Snapcast clients
```

MPD uses a machine-specific configuration for the Raspberry Pi audio output.
It also exposes a `fifo` output named `snapcast`, formatted as
`48000:16:2`. The Snapserver configuration reads this FIFO and publishes the
stream named `MPD`. `ympd` provides a web interface for controlling MPD.

### Minimal image as an audio endpoint

`mediaserver-image-minimal` is designed for a separate Raspberry Pi connected
to speakers. It installs `snapclient`, PulseAudio, the PulseAudio TCP native
protocol module, Zeroconf publishing, ALSA utilities, and network support.
It does not install MPD or Snapserver.

There are two supported uses for this image:

1. It receives the synchronized Snapcast stream from a MediaServer running
   `snapserver` and plays it locally.
2. It acts as a PulseAudio playback endpoint. An MPD instance on the central
   MediaServer can select the endpoint through an `audio_output` of type
   `pulse`, using the endpoint's PulseAudio native protocol over TCP.

The endpoint's `snapclient.conf` currently points to `192.168.1.5`; this is a
deployment-specific setting and should be changed for the target network.
The installed `snapclient.service` uses the ALSA card
`sysdefault:CARD=Headphones`, so the service configuration may also require a
machine-specific adjustment.

## Snapcast

Snapcast synchronizes one audio stream across multiple networked clients.
The full image contains both `snapserver` and `snapclient`; the minimal image
is intended primarily for `snapclient`.

The current setup uses:

- `snapserver.service` to run the server;
- `snapclient.service` to run clients;
- the MPD FIFO as the `MPD` server stream;
- PulseAudio as the local client audio backend;
- Avahi for service discovery;
- `/etc/snapserver.conf` and `/etc/snapclient.conf` for configuration.

The optional `snapcast-bt` package adds Bluetooth-aware stream switching on a
full image. It watches PulseAudio source events. When a `bluez_source` appears,
it creates a PulseAudio null sink and loopback, captures the Bluetooth audio
through a FIFO, and switches the first Snapcast group to the `Bluetooth`
stream. When the Bluetooth source disappears, it removes the temporary
PulseAudio modules and switches the group back to `MPD`.

This helper expects the local Snapserver JSON-RPC endpoint on port `1705` and
uses the stream names `MPD` and `Bluetooth`. It therefore depends on the
Snapserver configuration and group layout matching the script.

## MPD and PulseAudio

MPD is the central music player in the full image. Its configuration is
installed as `/etc/mpd.conf`, with a symlink under `/etc/mediaserver`. The
default music directory is `/home/Music`; playlists and the MPD database live
under `/var/lib/mpd`.

The supplied configurations provide:

- a local PulseAudio output;
- the Snapcast FIFO output;
- optional machine-specific files for Pi 3, Pi 4, and Zero 2 W;
- support for common formats and sources through the MPD recipe
  `PACKAGECONFIG` settings.

PulseAudio runs as a system service. The layer enables the native protocol over
TCP, Zeroconf publishing, Bluetooth discovery/device modules, loopback support,
and a small Raspberry Pi scheduling adjustment (`tsched=0`) intended to avoid
dropouts when switching between PulseAudio and Snapcast outputs.

The TCP native protocol is configured with anonymous authentication in the
current layer. Use it only on a trusted network or replace that policy with a
secured deployment-specific configuration.

## Bluetooth audio

Bluetooth support is supplied by BlueZ and PulseAudio. The common image policy
enables the `bluez5` and `bluetooth` distro features, while the audio package
group installs the PulseAudio Bluetooth discovery, policy, and device modules.

For the automatic Bluetooth-to-Snapcast path, install the `snapcast-bt`
package. Its `bt-snapcast-autoplug.service` listens for PulseAudio source
events and manages the temporary capture path. `pa-event-generator.service`
generates a short PulseAudio event during startup so the watcher can verify
that PulseAudio is ready.

Bluetooth device names, the default sink, and the first Snapcast group are
runtime assumptions. They should be checked on the target hardware rather
than copied blindly between Raspberry Pi devices.

## YouTube downloader

The `youtubedl` recipe installs the downloader from the `youtubedl-web`
project together with `yt-dlp`, FFmpeg, Mutagen, and the local metadata helper.
It installs:

- `/opt/YoutubeDownloader` and its playlist-management code;
- `/etc/mediaserver/youtubedl.ini`;
- `youtubedl.service`;
- `youtubedl.timer`.

The service runs the playlist manager using the configured YouTube playlist
URLs. The current sample configuration stores downloaded files below
`/mnt/TOSHIBA EXT/muzyka/Youtube list` and defines several named playlists.
That path is an example tied to an external storage device; it must be
changed to a directory present in the deployed image and compatible with
MPD's `music_directory`.

The downloader is scheduled by systemd. It is therefore a synchronization job,
not a live YouTube streaming service: it downloads files locally, after which
MPD can index and play them. YouTube access, content licensing, and the
stability of the pinned/project downloader code remain deployment concerns.

## YouTube DL Web

`youtubedl-web` is the browser-facing companion to the downloader. The recipe
installs a Flask application, static files, templates, playlist helpers, an
Apache configuration, and `youtubedl-web.service`. Apache proxies requests to
the application and exposes it below the `/youtubedl/` path.

The web application can manage downloads and playlists and includes an alarm
page. It depends on the `youtubedl` package, Apache, Python Flask components,
metadata handling, and the local `www-data` sudo policy used to control the
alarm services.

The web service writes its log to `/var/log/youtubedl-web.log` at runtime.
Logs and downloaded music are data, not immutable image configuration, and
should be backed up or migrated separately.

## Alarm using downloaded music

The `alarm` recipe installs a Python MPD client, configuration, and systemd
units:

- `alarm.timer` starts the regular alarm;
- `alarm_snooze.timer` supports the snooze path;
- `alarm.service` and `alarm_snooze.service` run `/opt/alarm`;
- `alarm_gui.service` is used by the Qt application to represent alarm state.

The alarm connects to MPD on `localhost:6600`, disables existing outputs,
selects the first output, sets a low starting volume, and then gradually raises
the volume up to the configured maximum. With `the_newest_songs = true`, it
selects recently modified files from MPD's music database. Otherwise it loads
the configured MPD playlist.

This means downloaded YouTube music can be used by the alarm after it has been
placed below MPD's music directory and indexed by MPD. The downloader and the
alarm are not a direct streaming chain: the downloader creates local files,
MPD indexes them, and the alarm controls MPD.

Alarm settings are in `/etc/mediaserver/alarm.ini`. The current defaults are a
starting volume of 6, a maximum volume of 80, five volume steps, and a
55-second interval between steps. The snooze/newest-song position is stored in
`/tmp/alarmConfig`, so it is runtime state and is not persistent across all
forms of reboot or image replacement.

## Other layer contents

The layer also contains recipes or append files for the MediaServer Qt
application, Quetzalcoatl, QNapi, Jellyfin, MiniDLNA, Samba, Transmission,
File Browser, Ampache, vsftpd, networking, system configuration, and Raspberry
Pi kernel/image integration. The package groups in
`recipes-core/packagegroups/` define most of the full image contents.

For exact package membership, service names, and installed paths, treat the
recipes as authoritative; this document describes the intended runtime
architecture of the current tree.
