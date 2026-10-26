#!/usr/bin/python3

"""Snapserver service state, status, lifecycle, and stream policy."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import dbus
import logging
import threading
import time
from typing import Any

from snapcast_control import SnapcastControl


class SnapserverService:
    """Own all operations that belong to the local Snapserver service.

    ``audio-manager.py`` supplies discovered clients and service health, while
    this class handles the Snapserver systemd state, ``Server.GetStatus``,
    Snapclient address extraction, service presence decisions, and group
    stream synchronization.
    """

    def __init__(
        self,
        host: str,
        port: int,
        stream_names: Mapping[str, str],
        client_key_resolver: Callable[[str], str],
        state_fallback_interval: float,
        stream_sync_interval: float,
        logger: logging.Logger,
        wakeup: Callable[[], None],
        state_changed: Callable[[bool], None],
    ) -> None:
        """Configure Snapserver JSON-RPC, systemd, and policy parameters."""
        self.control = SnapcastControl(host, port, dict(stream_names), logger)
        self.client_key_resolver = client_key_resolver
        self.state_fallback_interval = state_fallback_interval
        self.stream_sync_interval = stream_sync_interval
        self.logger = logger
        self.wakeup = wakeup
        self.state_changed = state_changed
        self.systemd_manager: Any | None = None
        self.active = False
        self.initialized = False
        self.transition_pending = False
        self.state_lock = threading.Lock()
        self.next_state_check = 0.0
        self.presence_request: bool | None = None
        self.current_mode: str | None = None
        self.next_stream_sync = 0.0

    @property
    def systemd_ready(self) -> bool:
        """Return whether the systemd manager proxy has been registered."""
        return self.systemd_manager is not None

    def set_systemd_manager(self, manager: Any, initial_active: bool) -> None:
        """Attach systemd and publish the service's initial ActiveState."""
        self.systemd_manager = manager
        self.next_state_check = time.monotonic() + self.state_fallback_interval
        self.set_active(initial_active)

    def set_active(self, active: bool) -> None:
        """Store an ActiveState notification and wake the controller."""
        active = bool(active)
        with self.state_lock:
            changed = active != self.active
            self.active = active
            if changed:
                self.transition_pending = True
        self.logger.debug(
            "Snapserver ActiveState: active=%s changed=%s",
            active,
            changed,
        )
        if changed:
            self.state_changed(active)
            self.wakeup()

    def state(self, now: float) -> bool:
        """Return cached ActiveState and refresh it on the fallback deadline."""
        if now >= self.next_state_check:
            self.set_active(self._read_active_state())
            self.next_state_check = now + self.state_fallback_interval
        with self.state_lock:
            return self.active

    def consume_transition(self) -> bool:
        """Return whether initialization or an ActiveState transition occurred."""
        with self.state_lock:
            if not self.initialized:
                self.initialized = True
                return True
            transition = self.transition_pending
            self.transition_pending = False
            return transition

    def reset_presence_request(self) -> None:
        """Forget the last lifecycle request after client topology changes."""
        self.presence_request = None

    def status_clients(self) -> dict[str, dict[str, Any]] | None:
        """Read and normalize Snapclient records from ``Server.GetStatus``."""
        clients: dict[str, dict[str, Any]] = {}
        try:
            status = self.control.request("Server.GetStatus")
            groups = status.get("result", {}).get("server", {}).get("groups", [])
            for group in groups:
                for client in group.get("clients", []):
                    host = client.get("host", {})
                    host_name = str(host.get("name", "")).strip()
                    if not host_name:
                        continue
                    client_id = self.client_key_resolver(host_name)
                    clients[client_id] = client
                    clients[host_name.lower()] = client
                    clients[f"Snapclient-{client_id}".lower()] = client
            self.logger.debug(
                "Snapserver status returned %d client records",
                len({id(client) for client in clients.values()}),
            )
            return clients
        except (OSError, ValueError, KeyError, AttributeError, TypeError) as exc:
            self.logger.debug("Snapserver status unavailable: %s", exc)
            return None

    def client_addresses(self) -> dict[str, set[str]]:
        """Extract IPv4 addresses reported by Snapserver for its clients."""
        addresses: dict[str, set[str]] = {}
        clients = self.status_clients()
        if clients is None:
            return addresses
        seen: set[int] = set()
        for client in clients.values():
            if id(client) in seen:
                continue
            seen.add(id(client))
            host = client.get("host", {})
            host_name = str(host.get("name", "")).strip()
            client_id = self.client_key_resolver(host_name)
            address = str(host.get("ip", ""))
            if "::ffff:" in address:
                address = address.rsplit("::ffff:", 1)[-1]
            if "." in address:
                addresses.setdefault(client_id, set()).add(address)
        self.logger.debug("Snapserver client addresses: %s", addresses)
        return addresses

    def addresses_for_client(
        self,
        client_key: str,
        discovered_addresses: Mapping[str, Iterable[str]],
    ) -> tuple[str, ...]:
        """Merge Avahi and Snapserver addresses for one physical device."""
        addresses: set[str] = set()
        for service_name, service_addresses in discovered_addresses.items():
            if self.client_key_resolver(service_name) == client_key.lower():
                addresses.update(str(address) for address in service_addresses)
        addresses.update(self.client_addresses().get(client_key.lower(), set()))
        result = tuple(address for address in addresses if ":" not in address)
        self.logger.debug(
            "Resolved Snapserver device addresses: client=%s addresses=%s",
            client_key,
            result,
        )
        return result

    def addresses_for_service(
        self,
        service_name: str,
        discovered_addresses: Mapping[str, Iterable[str]],
    ) -> tuple[str, ...]:
        """Merge Avahi and Snapserver addresses for one advertised service."""
        service_key = service_name.lower()
        addresses = set(str(address) for address in discovered_addresses.get(service_key, ()))
        client_key = self.client_key_resolver(service_name)
        addresses.update(self.client_addresses().get(client_key, set()))
        return tuple(address for address in addresses if ":" not in address)

    def reconcile_presence(
        self,
        known_clients: Iterable[str],
        device_availability: Mapping[str, bool],
        service_active: Mapping[str, bool],
        status_known: Mapping[str, bool],
    ) -> None:
        """Start or stop Snapserver based on healthy remote Snapclients."""
        if self.systemd_manager is None:
            return
        available_clients = tuple(
            service_name
            for service_name in known_clients
            if device_availability.get(
                self.client_key_resolver(service_name),
                True,
            )
        )
        self.logger.debug(
            "Snapserver presence input: active=%s clients=%s "
            "device_availability=%s service_active=%s status_known=%s request=%s",
            self.active,
            available_clients,
            device_availability,
            service_active,
            status_known,
            self.presence_request,
        )
        if not available_clients:
            should_run = False
        elif not self.active:
            # Avahi ItemNew is enough to start the server.  Once it is up,
            # status_known and lastSeen decide whether it should remain up.
            should_run = (
                self.presence_request is not False
                or any(
                    not status_known.get(service_name.lower(), False)
                    for service_name in available_clients
                )
            )
        else:
            status_ready = all(
                status_known.get(service_name.lower(), False)
                for service_name in available_clients
            )
            should_run = (
                not status_ready
                or any(
                    service_active.get(service_name.lower(), False)
                    for service_name in available_clients
                )
            )
        self.logger.debug("Snapserver presence decision: should_run=%s", should_run)
        if should_run == self.presence_request:
            return
        try:
            if should_run:
                self.systemd_manager.StartUnit("snapserver.service", "replace")
                self.logger.info("Starting Snapserver: remote Snapclient available")
            else:
                self.systemd_manager.StopUnit("snapserver.service", "replace")
                self.logger.info("Stopping Snapserver: no remote Snapclient available")
            self.presence_request = should_run
        except dbus.DBusException as exc:
            self.logger.warning("Could not change Snapserver state: %s", exc)

    def sync_stream(self, mode: str, now: float) -> bool:
        """Synchronize all Snapcast groups with the requested source stream."""
        if mode == self.current_mode and now < self.next_stream_sync:
            return False
        if not self.control.set_stream(mode):
            return False
        previous_mode = self.current_mode
        self.current_mode = mode
        self.next_stream_sync = now + self.stream_sync_interval
        if previous_mode != mode:
            self.logger.info("Active Snapcast source mode: %s", mode)
        return True

    def _read_active_state(self) -> bool:
        """Read ``snapserver.service`` ActiveState through systemd D-Bus."""
        try:
            bus = dbus.SystemBus()
            manager_object = bus.get_object(
                "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
            )
            manager = dbus.Interface(manager_object, "org.freedesktop.systemd1.Manager")
            unit_path = manager.GetUnit("snapserver.service")
            unit_object = bus.get_object("org.freedesktop.systemd1", unit_path)
            properties = dbus.Interface(unit_object, "org.freedesktop.DBus.Properties")
            return str(
                properties.Get("org.freedesktop.systemd1.Unit", "ActiveState")
            ) == "active"
        except dbus.DBusException as exc:
            self.logger.warning("Could not read snapserver.service state: %s", exc)
            return False
