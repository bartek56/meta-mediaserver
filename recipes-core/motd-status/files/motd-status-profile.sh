#!/bin/sh

if [ -n "${PS1-}" ]; then
    (
        lock_dir=/run/motd-status.lock
        if mkdir "$lock_dir" 2>/dev/null; then
            trap 'rmdir "$lock_dir"' EXIT HUP INT TERM
            @BINDIR@/motd-status >/dev/null 2>&1
        fi
    ) &
    motd_status_pid=$!
    # Keep the update asynchronous, but do not let interactive shells report
    # its normal completion as: [1]+ Done.
    if command -v disown >/dev/null 2>&1; then
        disown "$motd_status_pid" 2>/dev/null || :
    fi
fi
