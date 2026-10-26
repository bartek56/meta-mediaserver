#!/usr/bin/python3

"""MPD output-state monitoring used by audio-manager."""

from __future__ import annotations

import dbus
import logging
import threading
import time
from typing import Any
from collections.abc import Callable

from mpd import MPDClient


class MpdService:
    """Own MPD output checks and debounced restarts requested by topology changes."""

    def __init__(
        self,
        host: str,
        port: int,
        logger: logging.Logger,
        check_interval: float = 5.0,
        restart_debounce: float = 3.0,
    ) -> None:
        """Configure the MPD endpoint, polling interval, and restart debounce."""
        self.host = host
        self.port = port
        self.logger = logger
        self.check_interval = check_interval
        self.restart_debounce = restart_debounce
        self.client: MPDClient | None = None
        self.connected = False
        self.output_active = False
        self.next_output_check = 0.0
        self.systemd_manager: Any | None = None
        self.restart_lock = threading.Lock()
        self.restart_pending = False
        self.restart_due: float | None = None

    @property
    def next_deadline(self) -> float:
        """Return the next MPD output or restart deadline."""
        with self.restart_lock:
            restart_due = self.restart_due
        if restart_due is None:
            return self.next_output_check
        return min(self.next_output_check, restart_due)

    def set_systemd_manager(self, manager: Any) -> None:
        """Attach the systemd manager used for MPD restarts."""
        self.systemd_manager = manager

    def schedule_restart(self, wakeup: Callable[[], None] | None = None) -> None:
        """Schedule one debounced MPD restart after remote output changes."""
        with self.restart_lock:
            self.restart_pending = True
            if self.restart_due is None:
                self.restart_due = time.monotonic() + self.restart_debounce
            due = self.restart_due
        self.logger.debug("MPD restart scheduled: due_monotonic=%s", due)
        if wakeup is not None:
            wakeup()

    def restart_if_due(self, now: float) -> None:
        """Restart MPD when a pending topology change reached its deadline."""
        with self.restart_lock:
            if (
                not self.restart_pending
                or self.restart_due is None
                or now < self.restart_due
            ):
                return
            if self.systemd_manager is None:
                self.logger.debug("Cannot restart MPD yet: systemd manager unavailable")
                self.restart_due = now + self.restart_debounce
                return
            self.restart_pending = False
            self.restart_due = None
        try:
            self.systemd_manager.RestartUnit("mpd.service", "replace")
            self.logger.info("Restarting MPD: remote PulseAudio topology changed")
        except dbus.DBusException as exc:
            self.logger.warning("Could not restart MPD after topology change: %s", exc)

    def refresh_if_due(self, now: float) -> None:
        """Refresh the MPD Snapcast-output state when its polling deadline expires."""
        if now < self.next_output_check:
            return
        self.output_active = self.snapcast_output_enabled()
        self.next_output_check = now + self.check_interval

    def defer_output_check(self, now: float) -> None:
        """Avoid polling MPD while Snapserver is inactive."""
        self.next_output_check = now + self.check_interval

    def snapcast_output_enabled(self) -> bool:
        """Return whether MPD currently has the `snapcast` output enabled."""
        try:
            if self.client is None:
                self.client = MPDClient()
                self.client.timeout = 1
                self.client.idletimeout = 1
            if not self.connected:
                self.client.connect(self.host, self.port)
                self.connected = True
            outputs = self.client.outputs()
            enabled = any(
                output.get("outputname") == "snapcast"
                and output.get("outputenabled") in {"1", 1, True}
                for output in outputs
            )
            self.logger.debug(
                "MPD outputs: snapcast_enabled=%s outputs=%s",
                enabled,
                outputs,
            )
            return enabled
        except Exception as exc:
            self.logger.debug("MPD output state unavailable: %s", exc)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Close the MPD connection without raising during shutdown."""
        if self.client is None:
            return
        try:
            self.client.disconnect()
        except Exception:
            try:
                self.client.close()
            except Exception:
                pass
        self.connected = False


# Kept as a compatibility alias for code importing the old component name.
MpdControl = MpdService
