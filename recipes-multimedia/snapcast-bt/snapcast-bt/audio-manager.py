#!/usr/bin/python3

"""Manage Bluetooth audio routing and Snapcast client presence.

The controller deliberately keeps running when snapserver.service is stopped.
PulseAudio is controlled through pulsectl, snapserver state through systemd's
D-Bus API, MPD through python-mpd2, and Snapcast through its JSON-RPC socket.
"""

from __future__ import annotations

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
import json
import logging
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import threading
import time
from typing import Any

import pulsectl
from mpd import MPDClient


LOG = logging.getLogger("bt-snapcast")
logging.basicConfig(level=logging.INFO, format="[BT-SNAPCAST] %(message)s")
logging.getLogger("mpd").setLevel(logging.WARNING)

SINK_BT = "snapcast_bt"
SINK_PC = "snapcast_pc"
DIRECT_SINK = "alsa_output.headphones.stereo-fallback"
FIFO_BT = "/tmp/snapbtfifo"
FIFO_PC = "/tmp/snappcfifo"
STATE_DIR = Path("/run/bt-snapcast")
ACTIVE_CLIENTS_PATH = Path("/run/audio-manager/active-clients.json")

SNAPCAST_HOST = "127.0.0.1"
SNAPCAST_PORT = 1705
SNAPCAST_STREAM_MPD = "MPD"
SNAPCAST_STREAM_BT = "Bluetooth"
SNAPCAST_STREAM_PC = "PC"
SNAPCLIENT_SERVICE_TYPE = "_snapclient._tcp"
SNAPCLIENT_SERVICE_PREFIX = "Snapclient-"
PULSE_SERVER_SERVICE_TYPE = "_pulse-server._tcp"

CAPTURE_IDLE_TIMEOUT = 60.0
PULSE_SNAPSHOT_INTERVAL = 10.0
MPD_CHECK_INTERVAL = 5.0
SNAPCAST_SYNC_INTERVAL = 5.0
AVAHI_POLL_INTERVAL = 5
AVAHI_FAILURE_THRESHOLD = 3
SYSTEMD_STATE_FALLBACK_INTERVAL = 30.0
DEFAULT_GAIN = 1.2
MPD_RESTART_DEBOUNCE = 3.0


class Controller:
    def __init__(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        ACTIVE_CLIENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.stop_event = threading.Event()
        self.pulse_wakeup = threading.Event()
        self.pulse = pulsectl.Pulse("audio-manager")
        self.snapserver_active = False
        self.snapserver_initialized = False
        self.snapserver_transition_pending = False
        self.snapserver_state_lock = threading.Lock()
        self.current_mode: str | None = None
        self.current_bt_source: str | None = None
        self.current_bt_target: str | None = None
        self.bt_loopback_id: int | None = None
        self.captures: dict[str, int] = {}
        self.capture_idle_since: dict[str, float | None] = {"bt": None, "pc": None}
        self.mpd_active = False
        self.mpd_client: MPDClient | None = None
        self.mpd_connected = False
        self.next_mpd_check = 0.0
        self.next_snapcast_sync = 0.0
        self.next_snap_presence_check = 0.0
        self.next_pulse_snapshot = 0.0
        self.next_systemd_fallback = 0.0
        self.cached_sinks: list[Any] | None = None
        self.cached_sources: list[Any] | None = None
        self.cached_sink_inputs: list[Any] | None = None
        self.systemd_loop: Any | None = None
        self.systemd_manager: Any | None = None
        self.remote_snapclients: set[str] = set()
        self.remote_clients_lock = threading.Lock()
        self.avahi_discovery_ready = False
        self.snapserver_presence_request: bool | None = None
        self.local_snapclient_service = f"{SNAPCLIENT_SERVICE_PREFIX}{socket.gethostname()}"
        self.remote_pulse_servers: set[str] = set()
        self.pulse_server_instances: set[tuple[int, int, str]] = set()
        self.pulse_servers_lock = threading.Lock()
        self.client_addresses: dict[str, set[str]] = {}
        self.client_addresses_lock = threading.Lock()
        self.pulse_probe_failures: dict[str, int] = {}
        self.pulse_probe_failures_lock = threading.Lock()
        self.snap_probe_failures: dict[str, int] = {}
        self.snap_probe_failures_lock = threading.Lock()
        self.pulse_discovery_ready = False
        self.mpd_restart_pending = False
        self.mpd_restart_due: float | None = None
        self._write_active_clients()

    @staticmethod
    def _client_id_from_service(service_name: str, prefix: str) -> str:
        value = str(service_name)
        if value.lower().startswith(prefix.lower()):
            return value[len(prefix):]
        return value

    def _start_service_resolution(
        self,
        bus: Any,
        avahi: Any,
        interface: int,
        protocol: int,
        service_name: str,
        service_type: str,
        domain: str,
    ) -> None:
        try:
            resolver_path = avahi.ServiceResolverNew(
                int(interface),
                int(protocol),
                service_name,
                service_type,
                domain,
                -1,
                0,
            )
        except dbus.DBusException as exc:
            LOG.debug("Could not create Avahi resolver for %s: %s", service_name, exc)
            return

        def on_found(
            _interface: int,
            _protocol: int,
            _name: str,
            _service_type: str,
            _domain: str,
            _host: str,
            _address_protocol: int,
            address: str,
            _port: int,
            _txt: list[str],
            _flags: int,
        ) -> None:
            with self.client_addresses_lock:
                self.client_addresses.setdefault(service_name.lower(), set()).add(
                    str(address)
                )
            self._write_active_clients()
            bus.remove_signal_receiver(
                on_found,
                dbus_interface="org.freedesktop.Avahi.ServiceResolver",
                signal_name="Found",
                path=resolver_path,
            )

        bus.add_signal_receiver(
            on_found,
            dbus_interface="org.freedesktop.Avahi.ServiceResolver",
            signal_name="Found",
            path=resolver_path,
        )

    def _write_active_clients(self) -> None:
        clients: dict[str, dict[str, Any]] = {}
        with self.remote_clients_lock:
            snapclients = tuple(self.remote_snapclients)
        with self.pulse_servers_lock:
            pulse_servers = tuple(self.remote_pulse_servers)
        with self.client_addresses_lock:
            addresses = {
                key: sorted(values)
                for key, values in self.client_addresses.items()
            }
        snapclient_addresses = self._snapclient_api_addresses()

        for service_name in snapclients:
            client_id = self._client_id_from_service(
                service_name, SNAPCLIENT_SERVICE_PREFIX
            )
            key = client_id.lower()
            client_addresses = set(addresses.get(service_name.lower(), []))
            client_addresses.update(snapclient_addresses.get(key, set()))
            client = clients.setdefault(
                key,
                {
                    "id": client_id,
                    "hostname": f"{client_id}.local",
                    "addresses": sorted(client_addresses),
                    "pulse": {"active": False, "port": 4713},
                    "snapclient": {"active": False, "port": 1704},
                },
            )
            client["addresses"] = sorted(
                set(client.get("addresses", [])) | client_addresses
            )
            client["snapclient"]["active"] = True

        for service_name in pulse_servers:
            client_id = self._client_id_from_service(service_name, "pulse@")
            key = client_id.lower()
            client_addresses = set(addresses.get(service_name.lower(), []))
            client_addresses.update(snapclient_addresses.get(key, set()))
            client = clients.setdefault(
                key,
                {
                    "id": client_id,
                    "hostname": f"{client_id}.local",
                    "addresses": sorted(client_addresses),
                    "pulse": {"active": False, "port": 4713},
                    "snapclient": {"active": False, "port": 1704},
                },
            )
            client["addresses"] = sorted(
                set(client.get("addresses", [])) | client_addresses
            )
            client["pulse"]["active"] = True

        payload = {
            "schema": 1,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "clients": sorted(clients.values(), key=lambda item: item["id"].lower()),
        }
        temporary_path = ACTIVE_CLIENTS_PATH.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, ACTIVE_CLIENTS_PATH)

    def _snapclient_api_addresses(self) -> dict[str, set[str]]:
        addresses: dict[str, set[str]] = {}
        try:
            status = self._snapcast_request("Server.GetStatus")
            groups = status.get("result", {}).get("server", {}).get("groups", [])
            for group in groups:
                for client in group.get("clients", []):
                    host = client.get("host", {})
                    client_id = str(host.get("name", "")).lower()
                    address = str(host.get("ip", ""))
                    if "::ffff:" in address:
                        address = address.rsplit("::ffff:", 1)[-1]
                    if client_id and "." in address:
                        addresses.setdefault(client_id, set()).add(address)
        except (OSError, ValueError, KeyError, AttributeError):
            pass
        return addresses

    def _snapclient_api_connected(self) -> set[str] | None:
        connected: set[str] = set()
        try:
            status = self._snapcast_request("Server.GetStatus")
            groups = status.get("result", {}).get("server", {}).get("groups", [])
            for group in groups:
                for client in group.get("clients", []):
                    host = client.get("host", {})
                    client_id = str(host.get("name", "")).lower()
                    if client_id and client.get("connected") is True:
                        connected.add(client_id)
            return connected
        except (OSError, ValueError, KeyError, AttributeError):
            return None

    def _service_addresses(self, service_name: str) -> tuple[str, ...]:
        with self.client_addresses_lock:
            addresses = tuple(self.client_addresses.get(service_name.lower(), ()))
        service_id = service_name
        for prefix in ("pulse@", "snapclient-"):
            if service_id.lower().startswith(prefix):
                service_id = service_id[len(prefix):]
                break
        addresses = tuple(
            set(addresses)
            | self._snapclient_api_addresses().get(service_id.lower(), set())
        )
        return tuple(address for address in addresses if ":" not in address)

    @staticmethod
    def _arp_reachable(address: str) -> bool:
        try:
            for line in Path("/proc/net/arp").read_text(encoding="ascii").splitlines()[1:]:
                fields = line.split()
                if len(fields) >= 4 and fields[0] == address:
                    return bool(int(fields[2], 16) & 0x2)
        except (OSError, ValueError):
            pass
        return False

    def _network_reachable(self, service_name: str) -> bool:
        addresses = self._service_addresses(service_name)
        if not addresses:
            return False
        ping_available = False
        for address in addresses:
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", address],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=1.5,
                )
                ping_available = True
                if result.returncode == 0:
                    return True
            except subprocess.TimeoutExpired:
                ping_available = True
            except OSError:
                continue
        if not ping_available:
            return any(self._arp_reachable(address) for address in addresses)
        return False

    def _service_reachable(self, service_name: str, port: int) -> bool:
        ipv4_addresses = self._service_addresses(service_name)
        if not ipv4_addresses:
            return False
        for address in ipv4_addresses:
            try:
                with socket.create_connection((address, port), timeout=0.5):
                    return True
            except OSError:
                continue
        return False

    def start(self) -> None:
        self._install_signal_handlers()
        self._start_pulse_listener()
        self._start_systemd_listener()
        self.reconcile(force=True)

        while not self.stop_event.is_set():
            now = time.monotonic()
            timeout = min(
                max(0.0, self.next_mpd_check - now),
                max(0.0, self.next_pulse_snapshot - now),
                max(0.0, self.next_systemd_fallback - now),
                max(0.0, self.mpd_restart_due - now)
                if self.mpd_restart_due is not None
                else float("inf"),
            )
            woke = self.pulse_wakeup.wait(timeout=timeout)
            self.pulse_wakeup.clear()
            self.reconcile(force=woke)

    def stop(self) -> None:
        self.stop_event.set()
        self.pulse_wakeup.set()
        if self.systemd_loop is not None:
            self.systemd_loop.quit()
        self._stop_capture("bt")
        self._stop_capture("pc")
        self._remove_bluetooth_loopback()
        self._disconnect_mpd()
        try:
            self.pulse.close()
        except Exception:
            pass

    def _install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, lambda _signum, _frame: self.stop_event.set())
        signal.signal(signal.SIGINT, lambda _signum, _frame: self.stop_event.set())

    def _start_pulse_listener(self) -> None:
        thread = threading.Thread(target=self._pulse_listener, name="pulse-events", daemon=True)
        thread.start()

    def _pulse_listener(self) -> None:
        while not self.stop_event.is_set():
            try:
                with pulsectl.Pulse("bt-snapcast-events") as pulse:
                    pulse.event_mask_set("all")
                    def on_event(event: Any) -> None:
                        facility = str(getattr(event, "facility", ""))
                        if facility in {"sink-input", "source", "sink", "card", "module", "server"}:
                            self.pulse_wakeup.set()

                    pulse.event_callback_set(on_event)
                    pulse.event_listen()
            except Exception as exc:
                if not self.stop_event.is_set():
                    LOG.warning("PulseAudio event listener unavailable: %s", exc)
                    self.stop_event.wait(2.0)

    def _start_systemd_listener(self) -> None:
        thread = threading.Thread(
            target=self._systemd_listener,
            name="systemd-events",
            daemon=True,
        )
        thread.start()

    def _systemd_listener(self) -> None:
        try:
            main_loop = GLib.MainLoop()
            self.systemd_loop = main_loop
            bus = dbus.SystemBus(mainloop=DBusGMainLoop())
            manager_object = bus.get_object(
                "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
            )
            manager = dbus.Interface(manager_object, "org.freedesktop.systemd1.Manager")
            self.systemd_manager = manager
            unit_path = manager.GetUnit("snapserver.service")
            unit_object = bus.get_object("org.freedesktop.systemd1", unit_path)
            properties = dbus.Interface(unit_object, "org.freedesktop.DBus.Properties")
            self._set_snapserver_state(
                str(properties.Get("org.freedesktop.systemd1.Unit", "ActiveState")) == "active"
            )

            def on_properties_changed(interface: str, changed: dict[str, Any], _invalidated: list[str]) -> None:
                if interface == "org.freedesktop.systemd1.Unit" and "ActiveState" in changed:
                    self._set_snapserver_state(str(changed["ActiveState"]) == "active")

            bus.add_signal_receiver(
                on_properties_changed,
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path=unit_path,
            )

            try:
                avahi_object = bus.get_object("org.freedesktop.Avahi", "/")
                avahi = dbus.Interface(avahi_object, "org.freedesktop.Avahi.Server")
                browser_path = avahi.ServiceBrowserNew(
                    -1, -1, SNAPCLIENT_SERVICE_TYPE, "local", 0
                )

                def on_service_found(
                    _interface: int,
                    _protocol: int,
                    name: str,
                    _service_type: str,
                    _domain: str,
                    _flags: int,
                ) -> None:
                    service_name = str(name)
                    if service_name == self.local_snapclient_service:
                        return
                    self._start_service_resolution(
                        bus,
                        avahi,
                        _interface,
                        _protocol,
                        service_name,
                        _service_type,
                        _domain,
                    )
                    with self.remote_clients_lock:
                        changed = service_name not in self.remote_snapclients
                        self.remote_snapclients.add(service_name)
                    if changed:
                        LOG.info("Remote Snapclient discovered: %s", service_name)
                        self._write_active_clients()
                        self.pulse_wakeup.set()

                def on_service_removed(
                    _interface: int,
                    _protocol: int,
                    name: str,
                    _service_type: str,
                    _domain: str,
                    _flags: int,
                ) -> None:
                    service_name = str(name)
                    with self.remote_clients_lock:
                        changed = service_name in self.remote_snapclients
                        self.remote_snapclients.discard(service_name)
                    if changed:
                        LOG.info("Remote Snapclient removed: %s", service_name)
                        with self.client_addresses_lock:
                            self.client_addresses.pop(service_name.lower(), None)
                        self._write_active_clients()
                        self.pulse_wakeup.set()

                def on_all_for_now() -> None:
                    self.avahi_discovery_ready = True
                    LOG.info("Avahi Snapclient discovery ready")
                    self.pulse_wakeup.set()

                def remove_stale_snapclients(present: set[str]) -> None:
                    connected = self._snapclient_api_connected()
                    if connected is not None:
                        with self.remote_clients_lock:
                            known = set(self.remote_snapclients)
                        present = {
                            service_name for service_name in present
                            if (
                                self._client_id_from_service(
                                    service_name, SNAPCLIENT_SERVICE_PREFIX
                                ).lower() in connected
                                or service_name not in known
                            )
                        }
                    reachable: set[str] = set()
                    for service_name in present:
                        if self._network_reachable(service_name):
                            with self.snap_probe_failures_lock:
                                self.snap_probe_failures.pop(service_name, None)
                            reachable.add(service_name)
                            continue
                        with self.snap_probe_failures_lock:
                            failures = self.snap_probe_failures.get(service_name, 0) + 1
                            self.snap_probe_failures[service_name] = failures
                        if failures < AVAHI_FAILURE_THRESHOLD:
                            reachable.add(service_name)
                    present = reachable
                    with self.remote_clients_lock:
                        removed = self.remote_snapclients - present
                        added = present - self.remote_snapclients
                        self.remote_snapclients.update(present)
                        self.remote_snapclients.intersection_update(present)
                    if not removed and not added:
                        return
                    for service_name in sorted(removed):
                        LOG.info("Remote Snapclient expired from Avahi poll: %s", service_name)
                    self._write_active_clients()
                    self._schedule_mpd_restart()
                    self.pulse_wakeup.set()

                bus.add_signal_receiver(
                    on_service_found,
                    dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                    signal_name="ItemNew",
                    path=browser_path,
                )
                bus.add_signal_receiver(
                    on_service_removed,
                    dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                    signal_name="ItemRemove",
                    path=browser_path,
                )
                bus.add_signal_receiver(
                    on_all_for_now,
                    dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                    signal_name="AllForNow",
                    path=browser_path,
                )

                pulse_browser_path = avahi.ServiceBrowserNew(
                    -1, -1, PULSE_SERVER_SERVICE_TYPE, "local", 0
                )
                local_pulse_service = f"pulse@{socket.gethostname()}".lower()

                def on_pulse_server_found(
                    interface: int,
                    protocol: int,
                    name: str,
                    service_type: str,
                    domain: str,
                    _flags: int,
                ) -> None:
                    service_key = str(name).lower()
                    if service_key == local_pulse_service:
                        return
                    instance_key = (int(interface), int(protocol), service_key)
                    self._start_service_resolution(
                        bus,
                        avahi,
                        interface,
                        protocol,
                        str(name),
                        service_type,
                        domain,
                    )
                    schedule_restart = False
                    with self.pulse_servers_lock:
                        changed = service_key not in self.remote_pulse_servers
                        self.pulse_server_instances.add(instance_key)
                        self.remote_pulse_servers.add(service_key)
                        ready = self.pulse_discovery_ready
                        if changed and ready:
                            schedule_restart = True
                    if schedule_restart:
                        self._schedule_mpd_restart()
                    if changed:
                        LOG.info("Remote PulseAudio server discovered: %s", name)
                        self._write_active_clients()
                        self.pulse_wakeup.set()

                def on_pulse_server_removed(
                    _interface: int,
                    _protocol: int,
                    name: str,
                    _service_type: str,
                    _domain: str,
                    _flags: int,
                ) -> None:
                    service_name = str(name)
                    service_key = service_name.lower()
                    instance_key = (int(_interface), int(_protocol), service_key)
                    removed = False
                    schedule_restart = False
                    with self.pulse_servers_lock:
                        self.pulse_server_instances.discard(instance_key)
                        if not any(
                            item[2] == service_key for item in self.pulse_server_instances
                        ):
                            removed = service_key in self.remote_pulse_servers
                            self.remote_pulse_servers.discard(service_key)
                            if removed and self.pulse_discovery_ready:
                                schedule_restart = True
                    if schedule_restart:
                        self._schedule_mpd_restart()
                    if removed:
                        LOG.info("Remote PulseAudio service removed: %s", service_name)
                        with self.client_addresses_lock:
                            self.client_addresses.pop(service_key, None)
                        self._write_active_clients()
                        self.pulse_wakeup.set()

                def on_pulse_all_for_now() -> None:
                    self.pulse_discovery_ready = True
                    LOG.info("Avahi PulseAudio discovery ready")
                    self._schedule_mpd_restart()

                def remove_stale_pulse_servers(present: set[str]) -> None:
                    reachable: set[str] = set()
                    for service_name in present:
                        if self._service_reachable(service_name, 4713):
                            with self.pulse_probe_failures_lock:
                                self.pulse_probe_failures.pop(service_name, None)
                            reachable.add(service_name)
                            continue
                        with self.pulse_probe_failures_lock:
                            failures = self.pulse_probe_failures.get(service_name, 0) + 1
                            self.pulse_probe_failures[service_name] = failures
                        if failures < AVAHI_FAILURE_THRESHOLD:
                            reachable.add(service_name)
                    present = reachable
                    schedule_restart = False
                    with self.pulse_servers_lock:
                        removed = self.remote_pulse_servers - present
                        added = present - self.remote_pulse_servers
                        self.remote_pulse_servers.intersection_update(present)
                        self.remote_pulse_servers.update(present)
                        self.pulse_server_instances = {
                            item for item in self.pulse_server_instances
                            if item[2] in present
                        }
                        if (removed or added) and self.pulse_discovery_ready:
                            schedule_restart = True
                    if not removed and not added:
                        return
                    for service_key in sorted(removed):
                        LOG.info("Remote PulseAudio service expired from Avahi poll: %s", service_key)
                    if schedule_restart:
                        self._schedule_mpd_restart()
                    self._write_active_clients()
                    self.pulse_wakeup.set()

                def poll_service_type(
                    service_type: str,
                    on_complete: Any,
                ) -> None:
                    present: set[str] = set()
                    try:
                        poll_path = avahi.ServiceBrowserNew(
                            -1, -1, service_type, "local", 0
                        )
                    except dbus.DBusException as exc:
                        LOG.debug("Could not poll Avahi %s: %s", service_type, exc)
                        return

                    def cleanup() -> None:
                        for signal_name, callback in (
                            ("ItemNew", on_item_new),
                            ("AllForNow", on_poll_complete),
                        ):
                            bus.remove_signal_receiver(
                                callback,
                                dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                                signal_name=signal_name,
                                path=poll_path,
                            )
                        try:
                            browser_object = bus.get_object(
                                "org.freedesktop.Avahi", poll_path
                            )
                            dbus.Interface(
                                browser_object,
                                "org.freedesktop.Avahi.ServiceBrowser",
                            ).Free()
                        except dbus.DBusException:
                            pass

                    def on_item_new(
                        _interface: int,
                        _protocol: int,
                        name: str,
                        _service_type: str,
                        _domain: str,
                        _flags: int,
                    ) -> None:
                        present.add(str(name))

                    def on_poll_complete() -> None:
                        cleanup()
                        on_complete(present)

                    bus.add_signal_receiver(
                        on_item_new,
                        dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                        signal_name="ItemNew",
                        path=poll_path,
                    )
                    bus.add_signal_receiver(
                        on_poll_complete,
                        dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                        signal_name="AllForNow",
                        path=poll_path,
                    )

                def poll_avahi_presence() -> bool:
                    with self.pulse_servers_lock:
                        known_pulse_servers = set(self.remote_pulse_servers)
                    remove_stale_pulse_servers(known_pulse_servers)
                    poll_service_type(
                        SNAPCLIENT_SERVICE_TYPE,
                        lambda names: remove_stale_snapclients(
                            {
                                name for name in names
                                if name != self.local_snapclient_service
                            }
                        ),
                    )
                    poll_service_type(
                        PULSE_SERVER_SERVICE_TYPE,
                        lambda names: remove_stale_pulse_servers(
                            {
                                name.lower() for name in names
                                if name.lower() != local_pulse_service
                            }
                        ),
                    )
                    return True

                def enable_pulse_discovery_after_startup() -> bool:
                    if not self.pulse_discovery_ready:
                        self.pulse_discovery_ready = True
                        LOG.info("Avahi PulseAudio discovery ready (startup grace period)")
                    return False

                bus.add_signal_receiver(
                    on_pulse_server_found,
                    dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                    signal_name="ItemNew",
                    path=pulse_browser_path,
                )
                bus.add_signal_receiver(
                    on_pulse_server_removed,
                    dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                    signal_name="ItemRemove",
                    path=pulse_browser_path,
                )
                bus.add_signal_receiver(
                    on_pulse_all_for_now,
                    dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
                    signal_name="AllForNow",
                    path=pulse_browser_path,
                )
                GLib.timeout_add_seconds(5, enable_pulse_discovery_after_startup)
                GLib.timeout_add_seconds(AVAHI_POLL_INTERVAL, poll_avahi_presence)
            except dbus.DBusException as exc:
                LOG.warning("Avahi Snapclient discovery unavailable: %s", exc)
            main_loop.run()
        except dbus.DBusException as exc:
            LOG.warning("Snapserver D-Bus listener unavailable: %s", exc)
        except AttributeError as exc:
            LOG.warning("D-Bus dispatch is unavailable: %s", exc)

    def _set_snapserver_state(self, active: bool) -> None:
        with self.snapserver_state_lock:
            changed = active != self.snapserver_active
            self.snapserver_active = active
            if changed:
                self.snapserver_transition_pending = True
        if changed:
            self._write_active_clients()
            self.pulse_wakeup.set()

    def _schedule_mpd_restart(self) -> None:
        with self.pulse_servers_lock:
            self.mpd_restart_pending = True
            if self.mpd_restart_due is None:
                self.mpd_restart_due = time.monotonic() + MPD_RESTART_DEBOUNCE
        self.pulse_wakeup.set()

    def _restart_mpd_if_pending(self, now: float) -> None:
        with self.pulse_servers_lock:
            if (
                not self.mpd_restart_pending
                or self.mpd_restart_due is None
                or now < self.mpd_restart_due
            ):
                return
            self.mpd_restart_pending = False
            self.mpd_restart_due = None
        if self.systemd_manager is None:
            return
        try:
            self.systemd_manager.RestartUnit("mpd.service", "replace")
            LOG.info("Restarting MPD: remote PulseAudio topology changed")
        except dbus.DBusException as exc:
            LOG.warning("Could not restart MPD after PulseAudio topology change: %s", exc)

    def reconcile(self, force: bool = False) -> None:
        now = time.monotonic()
        self._restart_mpd_if_pending(now)
        self._reconcile_snapserver_presence()
        snapserver_active = self._snapserver_state(now)
        with self.snapserver_state_lock:
            transition_pending = self.snapserver_transition_pending
        if not self.snapserver_initialized or transition_pending:
            self.snapserver_initialized = True
            with self.snapserver_state_lock:
                self.snapserver_transition_pending = False
            LOG.info("Snapserver state: %s", "active" if snapserver_active else "inactive")
            if snapserver_active:
                self._ensure_snapcast_paths()
            else:
                self._stop_capture("bt")
                self._stop_capture("pc")

        if force or now >= self.next_pulse_snapshot or self.cached_sinks is None:
            try:
                self.cached_sinks = self.pulse.sink_list()
                self.cached_sources = self.pulse.source_list()
                self.cached_sink_inputs = self.pulse.sink_input_list()
                self.next_pulse_snapshot = now + PULSE_SNAPSHOT_INTERVAL
            except Exception as exc:
                LOG.warning("PulseAudio state unavailable: %s", exc)
                return

        sinks = self.cached_sinks or []
        sources = self.cached_sources or []
        sink_inputs = self.cached_sink_inputs or []
        bt_source = next(
            (source.name for source in sources if source.name.startswith("bluez_source")),
            None,
        )
        pc_active = self._sink_audio_active(SINK_PC, sinks, sink_inputs)
        bt_audio_active = self._sink_audio_active(SINK_BT, sinks, sink_inputs)

        bt_target = SINK_BT if self.snapserver_active else self._physical_sink_name(sinks)
        if bt_source != self.current_bt_source or bt_target != self.current_bt_target:
            if bt_source is None:
                self._remove_bluetooth_loopback()
            elif bt_target is not None:
                self._ensure_bluetooth_loopback(bt_source, bt_target)
            self.current_bt_source = bt_source
            self.current_bt_target = bt_target

        if not self.snapserver_active:
            self._stop_capture("bt")
            self._stop_capture("pc")
            self.next_mpd_check = now + MPD_CHECK_INTERVAL
            return

        if bt_audio_active:
            self.capture_idle_since["bt"] = None
            self._start_capture("bt", SINK_BT, FIFO_BT)
        else:
            self._stop_after_idle("bt", SINK_BT, FIFO_BT, now)

        if pc_active:
            self.capture_idle_since["pc"] = None
            self._start_capture("pc", SINK_PC, FIFO_PC)
        else:
            self._stop_after_idle("pc", SINK_PC, FIFO_PC, now)

        if now >= self.next_mpd_check:
            self.mpd_active = self._mpd_snapcast_active()
            self.next_mpd_check = now + MPD_CHECK_INTERVAL

        desired_mode = self._desired_mode(bt_source, pc_active)
        if desired_mode is not None and (
            desired_mode != self.current_mode or now >= self.next_snapcast_sync
        ):
            previous_mode = self.current_mode
            if self._set_snapcast_stream(desired_mode):
                self.current_mode = desired_mode
                self.next_snapcast_sync = now + SNAPCAST_SYNC_INTERVAL
                if previous_mode != desired_mode:
                    LOG.info("Active source mode: %s", desired_mode)

    def _reconcile_snapserver_presence(self) -> None:
        if not self.avahi_discovery_ready or self.systemd_manager is None:
            return
        now = time.monotonic()
        with self.remote_clients_lock:
            known_clients = set(self.remote_snapclients)
        if now >= self.next_snap_presence_check:
            reachable_clients = {
                service_name for service_name in known_clients
                if (
                    not self._service_addresses(service_name)
                    or self._network_reachable(service_name)
                )
            }
            self.next_snap_presence_check = now + AVAHI_POLL_INTERVAL
            if reachable_clients != known_clients:
                with self.remote_clients_lock:
                    self.remote_snapclients.intersection_update(reachable_clients)
                self._write_active_clients()
                self.pulse_wakeup.set()
        else:
            reachable_clients = known_clients
        should_run = bool(reachable_clients)
        if should_run == self.snapserver_presence_request:
            return
        try:
            if should_run:
                self.systemd_manager.StartUnit("snapserver.service", "replace")
                LOG.info("Starting Snapserver: remote Snapclient available")
            else:
                self.systemd_manager.StopUnit("snapserver.service", "replace")
                LOG.info("Stopping Snapserver: no remote Snapclient available")
            self.snapserver_presence_request = should_run
        except dbus.DBusException as exc:
            LOG.warning("Could not change Snapserver state from Avahi presence: %s", exc)

    def _desired_mode(self, bt_source: str | None, pc_active: bool) -> str | None:
        if bt_source is not None:
            return "bluetooth"
        if pc_active:
            return "pc"
        if self.mpd_active:
            return "mpd"
        if self.current_mode == "bluetooth":
            return "pc" if pc_active else "mpd"
        return "mpd"

    def _snapserver_state(self, now: float) -> bool:
        if now >= self.next_systemd_fallback:
            state = self._read_snapserver_state()
            self._set_snapserver_state(state)
            self.next_systemd_fallback = now + SYSTEMD_STATE_FALLBACK_INTERVAL
        with self.snapserver_state_lock:
            return self.snapserver_active

    @staticmethod
    def _read_snapserver_state() -> bool:
        try:
            bus = dbus.SystemBus()
            manager_object = bus.get_object(
                "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
            )
            manager = dbus.Interface(manager_object, "org.freedesktop.systemd1.Manager")
            unit_path = manager.GetUnit("snapserver.service")
            unit_object = bus.get_object("org.freedesktop.systemd1", unit_path)
            properties = dbus.Interface(unit_object, "org.freedesktop.DBus.Properties")
            return str(properties.Get("org.freedesktop.systemd1.Unit", "ActiveState")) == "active"
        except dbus.DBusException as exc:
            LOG.warning("Could not read snapserver.service state over D-Bus: %s", exc)
            return False

    def _find_sink(self, name: str, sinks: list[Any] | None = None) -> Any | None:
        if sinks is None:
            sinks = self.pulse.sink_list()
        return next((sink for sink in sinks if sink.name == name), None)

    def _physical_sink_name(self, sinks: list[Any] | None = None) -> str | None:
        sink = self._find_sink(DIRECT_SINK, sinks)
        if sink is not None:
            return sink.name
        default_name = self.pulse.server_info().default_sink_name
        if default_name and not default_name.startswith("snapcast_"):
            return default_name
        if sinks is None:
            sinks = self.pulse.sink_list()
        return next((sink.name for sink in sinks if sink.name.startswith("alsa_output.")), None)

    def _ensure_bluetooth_loopback(self, source_name: str, target_sink: str) -> None:
        desired_argument = f"source={source_name} sink={target_sink}"
        modules = [
            module for module in self.pulse.module_list()
            if module.name == "module-loopback"
            and f"source={source_name}" in module.argument
        ]
        matching = next((module for module in modules if desired_argument in module.argument), None)
        if matching is not None:
            self.bt_loopback_id = int(matching.index)
            return

        for module in modules:
            self.pulse.module_unload(module.index)
        self.bt_loopback_id = int(self.pulse.module_load(
            "module-loopback",
            f"source={source_name} sink={target_sink} latency_msec=10",
        ))
        LOG.info("Bluetooth route: %s -> %s", source_name, target_sink)
        time.sleep(0.2)
        self._set_loopback_volume(target_sink)

    def _remove_bluetooth_loopback(self) -> None:
        if self.current_bt_source is None:
            return
        for module in self.pulse.module_list():
            if module.name == "module-loopback" and f"source={self.current_bt_source}" in module.argument:
                self.pulse.module_unload(module.index)
        self.bt_loopback_id = None

    def _set_loopback_volume(self, sink_name: str) -> None:
        sink = self._find_sink(sink_name)
        if sink is None:
            return
        inputs = [item for item in self.pulse.sink_input_list() if item.sink == sink.index]
        if inputs:
            self.pulse.volume_set_all_chans(max(inputs, key=lambda item: item.index), DEFAULT_GAIN)

    def _ensure_snapcast_paths(self) -> None:
        self._ensure_null_sink(SINK_BT, "Snapcast_BT")
        self._ensure_null_sink(SINK_PC, "Snapcast_PC")
        self._ensure_fifo(FIFO_BT)
        self._ensure_fifo(FIFO_PC)

    def _ensure_null_sink(self, sink_name: str, description: str) -> None:
        if self._find_sink(sink_name) is None:
            self.pulse.module_load(
                "module-null-sink",
                f"sink_name={sink_name} sink_properties=device.description={description}",
            )

    @staticmethod
    def _ensure_fifo(path: str) -> None:
        if os.path.exists(path) and not stat.S_ISFIFO(os.stat(path).st_mode):
            os.unlink(path)
        if not os.path.exists(path):
            os.mkfifo(path)

    def _sink_audio_active(self, sink_name: str, sinks: list[Any], sink_inputs: list[Any]) -> bool:
        sink = self._find_sink(sink_name, sinks)
        if sink is None:
            return False
        return any(item.sink == sink.index and not item.corked for item in sink_inputs)

    def _start_capture(self, key: str, sink_name: str, fifo_path: str) -> None:
        process_id = self.captures.get(key)
        if process_id is not None and self._process_running(process_id):
            return
        try:
            process_id = os.posix_spawnp(
                "parec",
                [
                    "parec", "-d", f"{sink_name}.monitor",
                    "--format=s16le", "--rate=48000", "--channels=2",
                ],
                os.environ.copy(),
                file_actions=[
                    # Open the FIFO in the child.  A blocking open lets parec
                    # rendezvous with Snapserver when its reader is created.
                    (os.POSIX_SPAWN_OPEN, 1, fifo_path, os.O_WRONLY, 0o666),
                ],
            )
        except OSError as exc:
            LOG.warning("Could not start %s capture: %s", sink_name, exc)
            return
        self.captures[key] = process_id
        LOG.info("Started audio capture for %s", sink_name)

    def _stop_after_idle(self, key: str, sink_name: str, _fifo_path: str, now: float) -> None:
        if key not in self.captures:
            return
        if self.capture_idle_since[key] is None:
            self.capture_idle_since[key] = now
        elif now - self.capture_idle_since[key] >= CAPTURE_IDLE_TIMEOUT:
            self._stop_capture(key)
            LOG.info("Stopped idle audio capture for %s after %.0fs", sink_name, CAPTURE_IDLE_TIMEOUT)

    def _stop_capture(self, key: str) -> None:
        process_id = self.captures.pop(key, None)
        if process_id is None or not self._process_running(process_id):
            return
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and self._process_running(process_id):
            time.sleep(0.1)
        if self._process_running(process_id):
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self._reap_process(process_id)

    @staticmethod
    def _process_running(process_id: int) -> bool:
        try:
            os.kill(process_id, 0)
            return True
        except ProcessLookupError:
            return False

    @staticmethod
    def _reap_process(process_id: int) -> None:
        try:
            os.waitpid(process_id, 0)
        except ChildProcessError:
            pass

    def _mpd_snapcast_active(self) -> bool:
        try:
            if self.mpd_client is None:
                self.mpd_client = MPDClient()
                self.mpd_client.timeout = 1
                self.mpd_client.idletimeout = 1
            if not self.mpd_connected:
                self.mpd_client.connect("127.0.0.1", 6600)
                self.mpd_connected = True
            return any(
                output.get("outputname") == "snapcast"
                and output.get("outputenabled") in {"1", 1, True}
                for output in self.mpd_client.outputs()
            )
        except Exception as exc:
            LOG.debug("MPD output state unavailable: %s", exc)
            self._disconnect_mpd()
            return False

    def _disconnect_mpd(self) -> None:
        if self.mpd_client is None:
            return
        try:
            self.mpd_client.disconnect()
        except Exception:
            try:
                self.mpd_client.close()
            except Exception:
                pass
        self.mpd_connected = False

    def _snapcast_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {"id": 1, "jsonrpc": "2.0", "method": method}
        if params is not None:
            request["params"] = params
        with socket.create_connection((SNAPCAST_HOST, SNAPCAST_PORT), timeout=1.0) as connection:
            connection.sendall((json.dumps(request) + "\n").encode())
            data = b""
            while b"\n" not in data:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data += chunk
        return json.loads(data.splitlines()[0].decode())

    def _set_snapcast_stream(self, mode: str) -> bool:
        stream = {
            "bluetooth": SNAPCAST_STREAM_BT,
            "pc": SNAPCAST_STREAM_PC,
            "mpd": SNAPCAST_STREAM_MPD,
        }.get(mode)
        if stream is None:
            return False
        try:
            status = self._snapcast_request("Server.GetStatus")
            groups = status["result"]["server"]["groups"]
            groups_to_update = [
                group for group in groups if group.get("stream_id") != stream
            ]
            for group in groups_to_update:
                self._snapcast_request(
                    "Group.SetStream",
                    {"id": group["id"], "stream_id": stream},
                )
            return bool(groups)
        except (OSError, ValueError, KeyError, socket.timeout) as exc:
            LOG.warning("Snapcast control API unavailable: %s", exc)
            return False


def main() -> int:
    controller = Controller()
    try:
        controller.start()
    finally:
        controller.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
