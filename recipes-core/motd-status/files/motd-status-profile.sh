#!/bin/sh

if [ -n "${PS1-}" ]; then
    (
        lock_dir=/run/motd-status.lock
        if mkdir "$lock_dir" 2>/dev/null; then
            trap 'rmdir "$lock_dir"' EXIT HUP INT TERM
            @BINDIR@/motd-status >/dev/null 2>&1
        fi
    ) &
fi
