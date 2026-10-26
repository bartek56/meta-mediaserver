"""Avahi service discovery based only on ItemNew and ItemRemove events."""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any, Callable

from .events import ServiceDiscovered, ServiceRemoved, ServiceResolved
from .models import ServiceKey, ServiceKind


LOG = logging.getLogger("audio-manager.avahi")


class AvahiDiscovery:
    """Maintain the two permanent Avahi browsers required by the application."""

    def __init__(self, emit: Callable[[object], None]) -> None:
        self._emit = emit
        self._main_loop: Any | None = None
        self._thread: threading.Thread | None = None
        self._bus: Any | None = None
        self._resolvers: set[Any] = set()
        self._local_names = self._build_local_names()

    @staticmethod
    def _build_local_names() -> set[str]:
        """Build local hostname variants used to exclude local services."""

        names = {
            socket.gethostname().lower().rstrip("."),
            socket.getfqdn().lower().rstrip("."),
        }
        names.update({f"{name}.local" for name in tuple(names)})
        return names

    def _is_local(self, kind: ServiceKind, instance: str) -> bool:
        """Return whether an Avahi instance belongs to this machine."""

        value = instance.lower().rstrip(".")
        prefix = "snapclient-" if kind is ServiceKind.SNAPCLIENT else "pulse@"
        if value.startswith(prefix):
            value = value[len(prefix) :]
        return value in self._local_names or f"{value}.local" in self._local_names

    def start(self) -> None:
        """Start both Avahi browsers in a dedicated GLib thread."""

        def run() -> None:
            try:
                import dbus
                from dbus.mainloop.glib import DBusGMainLoop
                from gi.repository import GLib

                dbus_main_loop = DBusGMainLoop(set_as_default=True)
                bus = dbus.SystemBus(mainloop=dbus_main_loop)
                self._bus = bus
                root = bus.get_object("org.freedesktop.Avahi", "/")
                avahi = dbus.Interface(root, "org.freedesktop.Avahi.Server")
                self._create_browser(
                    bus,
                    avahi,
                    ServiceKind.SNAPCLIENT,
                    "_snapclient._tcp",
                )
                self._create_browser(
                    bus,
                    avahi,
                    ServiceKind.PULSE_AUDIO,
                    "_pulse-server._tcp",
                )
                self._main_loop = GLib.MainLoop()
                LOG.info("Avahi service browsers started")
                self._main_loop.run()
            except Exception:
                LOG.exception("Avahi discovery is unavailable")

        self._thread = threading.Thread(
            target=run,
            name="audio-manager-avahi",
            daemon=True,
        )
        self._thread.start()

    def _create_browser(
        self,
        bus: Any,
        avahi: Any,
        kind: ServiceKind,
        service_type: str,
    ) -> None:
        """Create one browser and attach only ItemNew/ItemRemove handlers."""

        import dbus

        browser_path = avahi.ServiceBrowserNew(-1, -1, service_type, "local", 0)

        def on_new(
            interface: int,
            protocol: int,
            name: str,
            _service_type: str,
            domain: str,
            _flags: int,
        ) -> None:
            instance = str(name)
            if self._is_local(kind, instance):
                LOG.debug("Ignoring local Avahi service %s", instance)
                return
            key = ServiceKey(kind, int(interface), int(protocol), instance)
            default_port = 1704 if kind is ServiceKind.SNAPCLIENT else 4713
            LOG.info("Avahi discovered %s service %s", kind.value, instance)
            self._emit(ServiceDiscovered(key=key, port=default_port))
            self._resolve(
                bus,
                avahi,
                key,
                service_type,
                domain,
                default_port,
            )

        def on_remove(
            interface: int,
            protocol: int,
            name: str,
            _service_type: str,
            _domain: str,
            _flags: int,
        ) -> None:
            instance = str(name)
            if self._is_local(kind, instance):
                return
            key = ServiceKey(kind, int(interface), int(protocol), instance)
            LOG.info("Avahi removed %s service %s", kind.value, instance)
            self._emit(ServiceRemoved(key=key))

        bus.add_signal_receiver(
            on_new,
            dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
            signal_name="ItemNew",
            path=browser_path,
        )
        bus.add_signal_receiver(
            on_remove,
            dbus_interface="org.freedesktop.Avahi.ServiceBrowser",
            signal_name="ItemRemove",
            path=browser_path,
        )

    def _resolve(
        self,
        bus: Any,
        avahi: Any,
        key: ServiceKey,
        service_type: str,
        domain: str,
        default_port: int,
    ) -> None:
        """Resolve one service and emit each resolved address."""

        import dbus

        try:
            resolver_path = avahi.ServiceResolverNew(
                key.interface,
                key.protocol,
                key.instance,
                service_type,
                domain,
                -1,
                0,
            )
        except dbus.DBusException as exc:
            LOG.warning("Could not resolve Avahi service %s: %s", key.instance, exc)
            return

        self._resolvers.add(resolver_path)

        def on_found(
            _interface: int,
            _protocol: int,
            _name: str,
            _service_type: str,
            _domain: str,
            _host: str,
            _address_protocol: int,
            address: str,
            port: int,
            _txt: list[str],
            _flags: int,
        ) -> None:
            resolved_port = int(port) if int(port) > 0 else default_port
            LOG.debug(
                "Avahi resolved %s to %s:%d",
                key.instance,
                address,
                resolved_port,
            )
            self._emit(
                ServiceResolved(
                    key=key,
                    address=str(address),
                    port=resolved_port,
                )
            )
            try:
                bus.remove_signal_receiver(
                    on_found,
                    dbus_interface="org.freedesktop.Avahi.ServiceResolver",
                    signal_name="Found",
                    path=resolver_path,
                )
            except dbus.DBusException:
                LOG.debug("Avahi resolver cleanup failed for %s", key.instance)
            self._resolvers.discard(resolver_path)

        bus.add_signal_receiver(
            on_found,
            dbus_interface="org.freedesktop.Avahi.ServiceResolver",
            signal_name="Found",
            path=resolver_path,
        )

    def stop(self) -> None:
        """Stop the GLib main loop used by Avahi callbacks."""

        if self._main_loop is not None:
            self._main_loop.quit()
