"""System-facing adapters used by the audio manager.

All potentially blocking operations live here.  The application invokes them
through :class:`audio_manager.scheduler.WorkerPool` and receives results back
on the main event-loop thread.
"""

from __future__ import annotations

import json
import logging
import socket
import subprocess
from typing import Any


LOG = logging.getLogger("audio-manager.adapters")


class PingProbe:
    """Run one IPv4 ICMP probe for a remote host."""

    def __init__(self, command: str = "ping", process_timeout: float = 2.0) -> None:
        self._command = command
        self._process_timeout = process_timeout

    def check(self, address: str) -> bool:
        """Return whether ``ping -c 1`` succeeds for ``address``.

        Args:
            address: IPv4 address to test.

        Returns:
            ``True`` for exit code zero, otherwise ``False``.

        The process timeout is a safety limit for a broken utility.  It does
        not replace the application-level consecutive-failure threshold.
        """

        try:
            result = subprocess.run(
                [self._command, "-c", "1", address],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=self._process_timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            LOG.debug("Ping probe failed for %s: %s", address, exc)
            return False
        return result.returncode == 0


class PulseAudioHandshakeProbe:
    """Perform a lightweight remote PulseAudio native-protocol handshake."""

    def __init__(self, command: str = "pactl") -> None:
        self._command = command

    def check(self, address: str, port: int, timeout: float) -> bool:
        """Return whether the remote PulseAudio server accepts a handshake.

        ``pactl info`` uses the PulseAudio native protocol and therefore
        validates more than an open TCP port.  Running it as a subprocess also
        gives the probe a hard timeout, including when the remote server stops
        responding during the handshake.
        """

        try:
            result = subprocess.run(
                [
                    self._command,
                    "-s",
                    f"tcp:{address}:{port}",
                    "info",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            LOG.debug("PulseAudio native handshake failed for %s:%d: %s", address, port, exc)
            return False
        return result.returncode == 0


class SnapcastRpcClient:
    """Minimal JSON-RPC client for the local Snapserver control socket."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1705,
        timeout: float = 1.0,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._request_id = 0

    def get_status(self) -> dict[str, Any]:
        """Return the result of ``Server.GetStatus``.

        Raises:
            OSError: If the socket cannot be opened or read.
            ValueError: If Snapserver returns malformed JSON or an RPC error.
        """

        self._request_id += 1
        request = {
            "id": self._request_id,
            "jsonrpc": "2.0",
            "method": "Server.GetStatus",
        }
        with socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        ) as connection:
            connection.sendall((json.dumps(request) + "\n").encode("utf-8"))
            data = b""
            while b"\n" not in data:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data += chunk
        if not data:
            raise ValueError("Snapserver returned an empty response")
        response = json.loads(data.splitlines()[0].decode("utf-8"))
        if "error" in response:
            raise ValueError(f"Snapserver RPC error: {response['error']}")
        return response


class SystemdUnitController:
    """Control and inspect one systemd unit through the system bus."""

    def __init__(self, unit_name: str) -> None:
        self._unit_name = unit_name

    def _manager(self) -> tuple[Any, Any]:
        """Return a system bus and the systemd manager interface."""

        import dbus
        from dbus.mainloop.glib import DBusGMainLoop

        dbus_main_loop = DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(mainloop=dbus_main_loop)
        object_proxy = bus.get_object(
            "org.freedesktop.systemd1",
            "/org/freedesktop/systemd1",
        )
        return bus, dbus.Interface(object_proxy, "org.freedesktop.systemd1.Manager")

    def active(self) -> bool:
        """Return whether the unit currently has ActiveState ``active``."""

        import dbus

        bus, manager = self._manager()
        unit_path = manager.GetUnit(self._unit_name)
        unit = bus.get_object("org.freedesktop.systemd1", unit_path)
        properties = dbus.Interface(unit, "org.freedesktop.DBus.Properties")
        return str(
            properties.Get("org.freedesktop.systemd1.Unit", "ActiveState")
        ) == "active"

    def start(self) -> None:
        """Request that systemd start the configured unit."""

        _, manager = self._manager()
        manager.StartUnit(self._unit_name, "replace")

    def stop(self) -> None:
        """Request that systemd stop the configured unit."""

        _, manager = self._manager()
        manager.StopUnit(self._unit_name, "replace")

    def restart(self) -> None:
        """Request that systemd restart the configured unit."""

        _, manager = self._manager()
        manager.RestartUnit(self._unit_name, "replace")


class SystemdUnitListener:
    """Listen for ActiveState changes for one unit in a GLib thread."""

    def __init__(self, unit_name: str) -> None:
        self._unit_name = unit_name
        self._thread: Any | None = None
        self._main_loop: Any | None = None

    def start(self, callback: Any) -> None:
        """Start D-Bus signal listening and call ``callback(bool)`` on changes."""

        import threading

        def run() -> None:
            try:
                import dbus
                from dbus.mainloop.glib import DBusGMainLoop
                from gi.repository import GLib

                dbus_main_loop = DBusGMainLoop(set_as_default=True)
                bus = dbus.SystemBus(mainloop=dbus_main_loop)
                manager_object = bus.get_object(
                    "org.freedesktop.systemd1",
                    "/org/freedesktop/systemd1",
                )
                manager = dbus.Interface(
                    manager_object,
                    "org.freedesktop.systemd1.Manager",
                )
                unit_path = manager.GetUnit(self._unit_name)
                unit = bus.get_object("org.freedesktop.systemd1", unit_path)
                properties = dbus.Interface(unit, "org.freedesktop.DBus.Properties")
                callback(
                    str(
                        properties.Get(
                            "org.freedesktop.systemd1.Unit", "ActiveState"
                        )
                    )
                    == "active"
                )

                def on_properties_changed(
                    interface: str,
                    changed: dict[str, Any],
                    _invalidated: list[str],
                ) -> None:
                    if interface == "org.freedesktop.systemd1.Unit" and "ActiveState" in changed:
                        callback(str(changed["ActiveState"]) == "active")

                bus.add_signal_receiver(
                    on_properties_changed,
                    dbus_interface="org.freedesktop.DBus.Properties",
                    signal_name="PropertiesChanged",
                    path=unit_path,
                )
                self._main_loop = GLib.MainLoop()
                self._main_loop.run()
            except Exception:
                LOG.exception("systemd D-Bus listener stopped unexpectedly")

        self._thread = threading.Thread(
            target=run,
            name="audio-manager-systemd",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the GLib listener thread if it is running."""

        if self._main_loop is not None:
            self._main_loop.quit()

