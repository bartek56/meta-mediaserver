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
import threading
from typing import Any, Callable


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


class PulseAudioEventListener:
    """Forward relevant events from a blocking ``pactl subscribe`` process."""

    _RELEVANT_OBJECTS = (
        "source",
        "source-output",
        "sink-input",
        "module",
    )

    def __init__(self, command: str = "pactl", retry_delay: float = 1.0) -> None:
        self._command = command
        self._retry_delay = retry_delay
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[str] | None = None
        self._process_lock = threading.Lock()

    def start(self, callback: Callable[[str], None]) -> None:
        """Start the listener thread and deliver relevant event lines.

        Args:
            callback: Function called with one filtered ``pactl subscribe``
                event line. The callback must return quickly; it is normally
                used only to post an event to the application loop.
        """

        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(callback,),
            name="audio-manager-pulse-events",
            daemon=True,
        )
        self._thread.start()

    def _run(self, callback: Callable[[str], None]) -> None:
        """Keep ``pactl subscribe`` alive and reconnect after failures."""

        while not self._stop_event.is_set():
            process: subprocess.Popen[str] | None = None
            try:
                process = subprocess.Popen(
                    [self._command, "subscribe"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )
                with self._process_lock:
                    self._process = process
                LOG.info("PulseAudio event subscription started")
                if process.stdout is None:
                    raise OSError("pactl subscribe did not provide stdout")
                for line in process.stdout:
                    if self._stop_event.is_set():
                        break
                    event = line.strip()
                    if not self.is_relevant_event(event):
                        continue
                    try:
                        callback(event)
                    except Exception:
                        LOG.exception("PulseAudio event callback failed")
                if not self._stop_event.is_set():
                    LOG.warning("pactl subscribe exited; retrying")
            except OSError as exc:
                if not self._stop_event.is_set():
                    LOG.warning("Could not start pactl subscribe: %s", exc)
            finally:
                self._terminate(process)
                with self._process_lock:
                    if self._process is process:
                        self._process = None
            if not self._stop_event.is_set():
                self._stop_event.wait(self._retry_delay)

    @classmethod
    def is_relevant_event(cls, event: str) -> bool:
        """Return whether an event can change local audio routing."""

        return event.startswith("Event ") and any(
            f" on {object_name} " in event
            for object_name in cls._RELEVANT_OBJECTS
        )

    @staticmethod
    def _terminate(process: subprocess.Popen[str] | None) -> None:
        """Terminate one listener process and wait briefly for cleanup."""

        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def stop(self) -> None:
        """Stop the listener process and join its thread."""

        self._stop_event.set()
        with self._process_lock:
            process = self._process
        self._terminate(process)
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None


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
        self._request_lock = threading.Lock()

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one JSON-RPC request and return its decoded response."""

        with self._request_lock:
            self._request_id += 1
            request_id = self._request_id
        request: dict[str, Any] = {
            "id": request_id,
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            request["params"] = params
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
            raise ValueError(f"Snapserver returned an empty response to {method}")
        response = json.loads(data.splitlines()[0].decode("utf-8"))
        if "error" in response:
            raise ValueError(f"Snapserver RPC error for {method}: {response['error']}")
        return response

    def get_status(self) -> dict[str, Any]:
        """Return the result of ``Server.GetStatus``.

        Raises:
            OSError: If the socket cannot be opened or read.
            ValueError: If Snapserver returns malformed JSON or an RPC error.
        """

        return self._request("Server.GetStatus")

    def set_all_groups_stream(self, stream_id: str) -> int:
        """Set the selected stream for every Snapcast group.

        Args:
            stream_id: Snapserver stream identifier, for example ``Bluetooth``.

        Returns:
            The number of groups for which a ``Group.SetStream`` request was
            sent. Groups already using ``stream_id`` are left unchanged.
        """

        status = self.get_status()
        groups = status.get("result", {}).get("server", {}).get("groups", [])
        changed = 0
        for group in groups:
            group_id = group.get("id")
            if not group_id or group.get("stream_id") == stream_id:
                continue
            self._request(
                "Group.SetStream",
                {"id": str(group_id), "stream_id": stream_id},
            )
            changed += 1
        return changed


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

