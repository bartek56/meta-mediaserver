# Safe configuration migration

This document describes what can be migrated from an existing MediaServer
device to a new image. It is based on the current `meta-mediaserver` tree and
should be reviewed whenever a recipe, service, machine, or upstream version
changes.

## What the migration script does

`scripts/migrate-config.py` runs on an administrative host. By default it only
reads the source and target systems and creates a local report. It does not
copy SSH host keys, secrets, network identity, application data, caches, or
runtime state.

The file manifest in `scripts/migration-files.txt` is the only source of paths
sent over SSH. Each entry has an explicit class and path:

```text
A /path/to/file
```

The script does not add directories recursively unless the manifest entry ends
with `/`. Classes `B`, `C`, and `D` are reported or require manual review. A
symbolic link is resolved for inventory and planning; the link itself is not
copied as file content.

The source-side operation is read-only: the script uses `tar -T -` and streams
the result over SSH. It does not use `sudo`, `su`, `scp`, `rsync`, package
installation, service restarts, or write commands on the source.

## Modes and example

`--inventory`/`--report` create a snapshot, `--plan` creates a migration plan,
`--diff` prepares a comparison report, `--dry-run` simulates the plan, and
`--apply` requires both `--plan-file` and `--yes`.

Only class A candidates can be applied automatically. An existing target file
is backed up before replacement. The script does not perform a global rollback
or restart services that were not active before migration.

```bash
scripts/migrate-config.py --plan \
  --source-host old-pi --source-user root \
  --target-host new-pi --target-user admin
```

Reports are written to `reports/config-migration/YYYY-MM-DD_HH-MM-SS/`.
Before applying a plan, review `comparison.tsv`, `migration-plan.tsv`, and the
diffs, then verify that the target has not changed since inventory collection.

## Configuration supplied by Yocto

The image is reproducible from recipes and `.bbappend` files. Prefer changing
the recipe or a deployment configuration over copying a complete `/etc` from
an old device.

| Area | Current source | Migration guidance |
| --- | --- | --- |
| MPD | `recipes-multimedia/mpd/mpd_%.bbappend` and `mpd.conf*` | Compare the machine-specific audio output and MPD version. Recreate from the recipe, then adjust the target hardware. |
| PulseAudio | `recipes-multimedia/pulseaudio/pulseaudio_%.bbappend` and `system.mediaserver.pa` | Migrate only shared policy. Verify the local sink, Bluetooth devices, and TCP exposure on the new Pi. |
| Snapcast | `recipes-multimedia/snapcast/snapcast_0.35.0.bb` and `snap*.conf` | Compare Snapcast versions, server address, stream names, and client sound card. Do not copy runtime state. |
| Bluetooth/Snapcast switching | `recipes-multimedia/snapcast-bt/` | Revalidate PulseAudio source names, Snapserver group layout, and Bluetooth hardware. The scripts assume stream names `MPD` and `Bluetooth`. |
| YouTube downloader | `recipes-multimedia/youtubedl/` | Recreate `youtubedl.ini`; review playlist URLs and the external-storage path. Downloaded files are application data and need a separate migration. |
| YouTube DL Web | `recipes-network/youtubedl-web/` | Recreate the recipe-provided Apache and service configuration. Review access control and the sudo policy manually. |
| Alarm | `recipes-app/alarm/` | Recreate `alarm.ini` and verify MPD's music directory, playlist, output selection, and timer policy. `/tmp/alarmConfig` is runtime state. |
| MiniDLNA | `recipes-multimedia/minidlna/` | Use the recipe as the configuration source. Treat media directories as user data. |
| Samba | `recipes-network/samba/` | Review shares, users, permissions, and credentials manually. |
| Transmission | `recipes-network/transmission/` | Compare settings with the new version; migrate the queue and downloaded data separately. |
| Network | `wpa-supplicant`, `dhcpcd`, and machine configuration | Manual review only. Do not overwrite the target's identity or connectivity automatically. |
| SSH | Image features and target `/etc/ssh` | Never copy host keys automatically. Review access credentials separately. |
| Service units | Most `recipes-*` directories | Compare with the units installed by the new image. Do not migrate generated runtime state. |
| MediaServer applications | `recipes-app/mediaserver*`, `configscript*`, and `system-configurator*` | Recreate application configuration and user input; do not copy generated first-boot state blindly. |
| PHP/Apache/FTP | `recipes-network/apache2`, `php`, and `vsftpd` | Manual review; secrets and access credentials are excluded. |
| Runtime data | `/var/lib`, `/var/cache`, and `/var/log` | Separate data-migration project. These paths are not immutable image configuration. |

## Audio-specific checks

The target machine must use the correct `MACHINE` and audio hardware. MPD
configuration differs for the Pi 3, Pi 4, and Zero 2 W. A minimal image may
need only a new PulseAudio endpoint address and ALSA card, while a base image
also needs MPD, Snapserver, and Bluetooth validation.

The minimal image's PulseAudio native protocol is currently configured for
anonymous TCP authentication. Treat the network as trusted or change the
policy before exposing it outside the local network.

YouTube downloads must be available below the target MPD `music_directory` and
must be indexed before the alarm can use them. Moving only `youtubedl.ini` does
not move the downloaded music.

## Apply and recovery

Before `--apply`, the script checks `mpd`, `snapserver`, `snapclient`,
`minidlna`, `pulseaudio`, `transmission-daemon`, `smbd`, and `jellyfin` over
SSH. It stops only services that are active, applies the approved files, and
starts only those services that were active before the migration. SSH and
network services are not stopped.

An existing target file is copied to a backup before replacement. Restore only
the specific file needed after checking the backup, then validate the affected
service manually. There is no automatic rollback of application data or
runtime directories.
