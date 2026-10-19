# AGENTS.md

## Project scope

meta-mediaserver is a Yocto layer for MediaServer. The primary supported
Yocto release is Wrynose 6.0, with the Raspberry Pi machines listed in
README.md.

## Change guidelines

- Preserve compatibility with BitBake 2.18 and Wrynose.
- Use ${UNPACKDIR} for source files; do not use ${WORKDIR} in recipe paths.
- Use SPDX license identifiers such as GPL-2.0-only, LGPL-3.0-only,
  and BSD-2-Clause.
- Every local patch must contain an Upstream-Status header.
- Do not disable QA globally. Fix the cause in the recipe, configuration,
  or source patch.
- All installed files must be included in FILES:*.
- For usrmerge, use ${bindir}, ${libdir}, and ${systemd_system_unitdir}
  instead of hard-coded /bin, /lib, or /lib/systemd paths.
- CMake changes must support CMake 4. Projects requiring a version older
  than 3.5 must be fixed with a patch or in do_configure.
- Use the existing Qt5 classes (cmake_qt5, qmake5) according to the
  current recipe. Qt6 migration requires a separate decision and
  application changes.

## Docker and BitBake

Run commands from the project root. Compose uses Ubuntu 26.04, mounts
the whole project, and starts Bash by default:

    docker compose run --rm yocto
    docker compose run --rm yocto bitbake <recipe>

Example recipe-level tests:

    docker compose run --rm yocto bitbake <recipe> -c configure -f
    docker compose run --rm yocto bitbake <recipe> -c compile -f
    docker compose run --rm yocto bitbake <recipe> -c package_qa -f
    docker compose run --rm yocto bitbake <recipe> -c populate_lic -f

For hosts with limited memory, reduce parallelism:

    docker compose run --rm -e BB_NUMBER_THREADS=2 -e PARALLEL_MAKE=-j2 \
        yocto bitbake <recipe>

Before building a complete image, test the task that reported the error.
Build the full Qt5 image with:

    docker compose run --rm yocto bitbake mediaserver-image-qt5

## Change verification

After making changes:

1. Run the relevant BitBake task with -f.
2. Check for new QA warnings.
3. If the change affects an image, run at least:

    docker compose run --rm yocto \
        bitbake mediaserver-image-base -c do_image_rpi_sdimg -f

4. Check the artifacts in build/tmp/deploy/images/<machine>/.

Do not remove tmp or sstate-cache without a clear reason. Remove
build/bitbake.lock and build/bitbake.sock only when the BitBake server
has stopped and no BitBake process is running.

## Documentation and configuration

- User documentation: README.md
- Layer setup script: conf/setup.sh
- Sample configurations: conf/yocto_conf/
- Docker files: conf/docker/

When changing the Yocto branch, update setup.sh, layer.conf,
bblayers.conf.sample, local.conf samples, and Dockerfile/Compose if
the host requirements change.
