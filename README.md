# meta-mediaserver

Yocto layer for the MediaServer project, maintained for the Yocto
Project Wrynose (6.0).

## Supported hardware

- Raspberry Pi Zero 2 W
- Raspberry Pi 3B
- Raspberry Pi 4 / 4B

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

The Qt5 variant requires:

```bash
cp sources/meta-mediaserver/conf/yocto_conf/local.conf.qt5.sample \
    build/conf/local.conf
```

The variant without a GUI uses:

```bash
cp sources/meta-mediaserver/conf/yocto_conf/local.conf.base.sample \
    build/conf/local.conf
```

Wrynose still supports Qt5 through the `meta-qt5` layer. The MediaServer
application recipes currently use `cmake_qt5`, `qmake5`, and `qt5.inc`.
Migrating to Qt6 requires separate application and recipe changes.

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
