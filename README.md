# meta-mediaserver

Yocto layer for the MediaServer project, maintained for the Yocto
Project Wrynose (6.0).

## Supported hardware

- Raspberry Pi Zero 2 W
- Raspberry Pi 3B
- Raspberry Pi 4 / 4B

The BSP already supplies the 64-bit machine definitions used by the layer:
`raspberrypi0-2w-64`, `raspberrypi3-64`, and `raspberrypi4-64`. The layer
does not duplicate those machine files. Select `MACHINE` in the build
configuration; it is not fixed by an image recipe.

The default machine is `raspberrypi4-64`. It can be changed in
`build/conf/local.conf`.

## Requirements

- Docker with Docker Compose
- at least 150 GB of free disk space
- Internet access for downloading layers and sources

The build container uses Ubuntu 26.04 and the `builder` user.

## Project setup

Run these commands from the project root:

```bash
mkdir -p sources
git clone -b wrynose https://github.com/bartek56/meta-mediaserver \
    sources/meta-mediaserver
bash sources/meta-mediaserver/conf/setup.sh
docker compose build yocto
```

The `conf/setup.sh` script downloads the Wrynose layers, BitBake 2.18
and the required dependency layers. It creates `build/conf/bblayers.conf`
and `build/conf/local.conf` if they do not already exist.

If the host user UID/GID is not 1000:

```bash
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
docker compose build yocto
```

## Running the container

Compose starts a clean Bash shell by default:

```bash
docker compose run --rm yocto
```

BitBake commands can be passed directly:

```bash
docker compose run --rm yocto bitbake mediaserver-image-base
docker compose run --rm yocto bitbake mediaserver-image-qt5
docker compose run --rm yocto bitbake mediaserver-image-minimal
```

The three images are independent. `mediaserver-image-minimal` is the
headless Snapcast/PulseAudio endpoint, `mediaserver-image-base` is the full
non-Qt server image, and `mediaserver-image-qt5` adds the Qt5 applications and
MediaServer splash screen. Only the Qt5 image inherits the optional display
profile marker; no image recipe installs Qt5 implicitly.

The Qt5 variant requires:

```bash
docker compose run --rm yocto bitbake \
    -R conf/yocto_conf/qt5-hdmi.conf \
    mediaserver-image-qt5
```

The `-R` fragment adds Qt5 and the product HDMI/display profile only for
this BitBake invocation. It avoids replacing `build/conf/local.conf` and
keeps the profile away from the `base` and `minimal` images.

`-R` resolves relative paths through BitBake's `BBPATH`. Since the
`meta-mediaserver` layer is in `BBPATH`, `conf/yocto_conf/qt5-hdmi.conf`
resolves to the file in that layer. Do not use
`sources/meta-mediaserver/conf/yocto_conf/qt5-hdmi.conf` with `-R`: BitBake
would search for that path below each `BBPATH` entry and fail. An absolute
container path is also valid:

```bash
docker compose run --rm yocto bitbake \
    -R /home/builder/yocto-project/sources/meta-mediaserver/conf/yocto_conf/qt5-hdmi.conf \
    mediaserver-image-qt5
```

The default `build/conf/local.conf` created by `setup.sh` is suitable for the
non-Qt image:

```bash
bitbake mediaserver-image-base
bitbake mediaserver-image-minimal
```

Set `MACHINE = "raspberrypi4-64"` (or another BSP-provided machine) in
`build/conf/local.conf`. The image target selects the package set; the
optional `qt5-hdmi.conf` fragment selects Qt5 and the firmware display
settings for the Qt5 build.

Wrynose still supports Qt5 through the `meta-qt5` layer. The MediaServer
application recipes currently use `cmake_qt5`, `qmake5`, and `qt5.inc`.
Migrating to Qt6 requires separate application and recipe changes.

### Raspberry Pi display configuration

The Raspberry Pi BSP's `rpi-config` recipe consumes `HDMI_*`, `HDMI_CVT`,
`VC4DTBO`, `GPU_MEM_1024`, `ENABLE_UART`, `ENABLE_SPI_BUS`,
`DISABLE_OVERSCAN`, `DISABLE_RPI_BOOT_LOGO`, and `RPI_EXTRA_CONFIG` while it
generates `config.txt`. These are therefore kept in `local.conf` or a
machine configuration, not in an image class. The
`mediaserver-image-hdmi` class is an explicit image opt-in/documentation
marker and does not install Qt or alter boot firmware settings.

The ADS7846 touchscreen lines in the Qt5 sample are independent of HDMI.
`KERNEL_DEVICETREE` should only name overlays that the selected kernel builds;
the standard Wrynose BSP does not list `overlays/ads7846.dtbo`, so the sample
uses the firmware `RPI_EXTRA_CONFIG` overlay instead. Validate that the
panel's firmware overlay is present for the selected Raspberry Pi before
deploying it. `VC4DTBO` remains machine-dependent: Pi 3/Zero 2 W use FKMS,
while Pi 4's BSP default is KMS.

## Images and artifacts

Images are stored in:

```
build/tmp/deploy/images/<machine>/
```

For Raspberry Pi 4:

```
build/tmp/deploy/images/raspberrypi4-64/
```

`rpi-sdimg` images use a 128 MiB boot partition, which is large enough
for the Raspberry Pi kernel and overlays.

## Layer contents

The layer integrates MediaServer, Quetzalcoatl, QNapi, File Browser,
Ampache, Transmission, MPD, ympd, MiniDLNA, Tvheadend, Samba, yt-dlp,
and vsftpd.

## Troubleshooting

After changing a recipe, a specific task can be forced:

```bash
docker compose run --rm yocto bitbake <recipe> -c configure -f
docker compose run --rm yocto bitbake <recipe> -c package_qa -f
docker compose run --rm yocto bitbake <recipe> -c populate_lic -f
```

Task logs are stored in:

```
build/tmp/work/<tune>-poky-linux/<recipe>/<version>/temp/
```

Common Wrynose failures involve SPDX identifiers, `WORKDIR`/`UNPACKDIR`
paths, old CMake versions, and build-time paths left in artifacts.
Do not disable QA without a clear reason; fix the issue in the recipe or
the source patch.

## Licensing

This layer contains recipes and patches from multiple upstream projects.
The license for each component is declared in its recipe.
