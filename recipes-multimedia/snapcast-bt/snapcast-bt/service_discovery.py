#!/usr/bin/python3

"""systemd and Avahi event listener for audio-manager."""

from __future__ import annotations

from typing import Any
import socket

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib


class ServiceDiscovery:
    """Keep permanent Avahi browsers and forward events to the controller."""

    def __init__(
        self,
        controller: Any,
        snapclient_service_type: str,
        pulse_service_type: str,
        logger: Any,
    ) -> None:
        """Configure permanent systemd and Avahi browser registration."""
        self.controller = controller
        self.snapclient_service_type = snapclient_service_type
        self.pulse_service_type = pulse_service_type
        self.logger = logger
        self.main_loop: Any | None = None
        self.bus: Any | None = None
        self.avahi: Any | None = None
        self.snapclient_registered = False
        self.pulse_registered = False
        self.retry_scheduled = False

    def run(self) -> None:
        """Run the GLib loop without swallowing unexpected programming errors."""
        self.main_loop = GLib.MainLoop()
        self.controller.systemd_loop = self.main_loop
        self._initialize()
        self.main_loop.run()

    def _initialize(self) -> None:
        """Perform one explicit initialization attempt and schedule retries."""
        if self.controller.stop_event.is_set():
            return
        if self.bus is None and not self._connect_bus():
            self._schedule_retry()
            return
        if not self.controller.snapserver_service.systemd_ready and not self._register_systemd():
            self._schedule_retry()
            return
        if not self.snapclient_registered or not self.pulse_registered:
            if not self._register_avahi_browsers():
                self._schedule_retry()
                return
        self.logger.debug(
            "Service discovery ready: systemd=%s snapclient=%s pulse=%s",
            self.controller.snapserver_service.systemd_ready,
            self.snapclient_registered,
            self.pulse_registered,
        )

    def _connect_bus(self) -> bool:
        """Connect to the system bus, handling only expected D-Bus failures."""
        try:
            self.bus = dbus.SystemBus(mainloop=DBusGMainLoop())
        except dbus.DBusException as exc:
            self.logger.warning("Could not connect to systemd/Avahi D-Bus: %s", exc)
            return False
        self.logger.debug("Connected to system D-Bus")
        return True

    def _register_systemd(self) -> bool:
        """Register Snapserver ActiveState notifications with systemd."""
        controller = self.controller
        bus = self.bus
        if bus is None:
            return False
        try:
            manager_object = bus.get_object(
                "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
            )
            manager = dbus.Interface(manager_object, "org.freedesktop.systemd1.Manager")
            unit_path = manager.GetUnit("snapserver.service")
            unit_object = bus.get_object("org.freedesktop.systemd1", unit_path)
            properties = dbus.Interface(unit_object, "org.freedesktop.DBus.Properties")
            active = str(
                properties.Get("org.freedesktop.systemd1.Unit", "ActiveState")
            ) == "active"

            def on_properties_changed(
                interface: str,
                changed: dict[str, Any],
                _invalidated: list[str],
            ) -> None:
                """Forward Snapserver ActiveState changes to the controller."""
                if interface == "org.freedesktop.systemd1.Unit" and "ActiveState" in changed:
                    self.logger.debug(
                        "systemd snapserver ActiveState changed: %s",
                        changed["ActiveState"],
                    )
                    controller.snapserver_service.set_active(
                        str(changed["ActiveState"]) == "active"
                    )

            bus.add_signal_receiver(
                on_properties_changed,
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path=unit_path,
            )
        except dbus.DBusException as exc:
            self.logger.warning("Could not register systemd listener: %s", exc)
            return False

        controller.snapserver_service.set_systemd_manager(manager, active)
        controller.mpd_service.set_systemd_manager(manager)
        self.logger.debug("systemd listener registered")
        return True

    def _register_avahi_browsers(self) -> bool:
        """Register the permanent Snapclient and PulseAudio Avahi browsers."""
        bus = self.bus
        if bus is None:
            return False
        try:
            avahi_object = bus.get_object("org.freedesktop.Avahi", "/")
            self.avahi = dbus.Interface(avahi_object, "org.freedesktop.Avahi.Server")
            self.logger.debug("Connected to Avahi D-Bus")
            if not self.snapclient_registered:
                self._register_snapclient_browser(bus, self.avahi)
                self.snapclient_registered = True
            if not self.pulse_registered:
                self._register_pulse_browser(bus, self.avahi)
                self.pulse_registered = True
        except dbus.DBusException as exc:
            self.logger.warning("Could not register Avahi browsers: %s", exc)
            return False
        return True

    def _schedule_retry(self) -> None:
        """Schedule one five-second initialization retry without a retry loop."""
        if self.retry_scheduled or self.controller.stop_event.is_set():
            return
        self.retry_scheduled = True
        self.logger.debug("Scheduling service-discovery retry in 5 seconds")

        def retry() -> bool:
            """Run one delayed initialization attempt and remove the timer."""
            self.retry_scheduled = False
            self._initialize()
            return False

        GLib.timeout_add_seconds(5, retry)

    def _register_snapclient_browser(self, bus: Any, avahi: Any) -> None:
        """Register ItemNew/ItemRemove handlers for remote Snapclients."""
        controller = self.controller
        browser_path = avahi.ServiceBrowserNew(
            -1, -1, self.snapclient_service_type, "local", 0
        )

        def on_service_found(
            interface: int,
            protocol: int,
            name: str,
            service_type: str,
            domain: str,
            _flags: int,
        ) -> None:
            """Handle a newly advertised remote Snapclient service."""
            service_name = str(name)
            self.logger.debug(
                "Avahi ItemNew: type=%s service=%s",
                self.snapclient_service_type,
                service_name,
            )
            if service_name == controller.local_snapclient_service:
                self.logger.debug("Ignoring local Snapclient service: %s", service_name)
                return
            controller.monitor_coordinator.ensure_service(service_name)
            controller._start_service_resolution(
                bus,
                avahi,
                interface,
                protocol,
                service_name,
                service_type,
                domain,
            )
            with controller.remote_clients_lock:
                changed = service_name not in controller.remote_snapclients
                controller.remote_snapclients.add(service_name)
            if changed:
                self.logger.info("Remote Snapclient discovered: %s", service_name)
                controller.monitor_coordinator.mark_snapcast_status_unknown(service_name)
                controller.snapserver_service.reset_presence_request()
                controller.mpd_service.schedule_restart(controller.pulse_wakeup.set)
                controller._write_active_clients()
                controller.pulse_wakeup.set()

        def on_service_removed(
            _interface: int,
            _protocol: int,
            name: str,
            _service_type: str,
            _domain: str,
            _flags: int,
        ) -> None:
            """Handle explicit removal of a remote Snapclient service."""
            service_name = str(name)
            self.logger.debug(
                "Avahi ItemRemove: type=%s service=%s",
                self.snapclient_service_type,
                service_name,
            )
            with controller.remote_clients_lock:
                changed = service_name in controller.remote_snapclients
                controller.remote_snapclients.discard(service_name)
            if changed:
                self.logger.info("Remote Snapclient removed: %s", service_name)
                controller.mpd_service.schedule_restart(controller.pulse_wakeup.set)
                with controller.client_addresses_lock:
                    controller.client_addresses.pop(service_name.lower(), None)
                controller.monitor_coordinator.remove_service(service_name)
                controller._write_active_clients()
                controller.pulse_wakeup.set()

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

    def _register_pulse_browser(self, bus: Any, avahi: Any) -> None:
        """Register ItemNew/ItemRemove handlers for remote PulseAudio servers."""
        controller = self.controller
        browser_path = avahi.ServiceBrowserNew(
            -1, -1, self.pulse_service_type, "local", 0
        )
        local_pulse_service = f"pulse@{socket.gethostname()}".lower()

        def on_service_found(
            interface: int,
            protocol: int,
            name: str,
            service_type: str,
            domain: str,
            _flags: int,
        ) -> None:
            """Handle a newly advertised remote PulseAudio service."""
            service_key = str(name).lower()
            self.logger.debug(
                "Avahi ItemNew: type=%s service=%s",
                self.pulse_service_type,
                service_key,
            )
            if service_key == local_pulse_service:
                self.logger.debug("Ignoring local PulseAudio service: %s", service_key)
                return
            instance_key = (int(interface), int(protocol), service_key)
            controller._start_service_resolution(
                bus,
                avahi,
                interface,
                protocol,
                str(name),
                service_type,
                domain,
            )
            with controller.pulse_servers_lock:
                changed = service_key not in controller.remote_pulse_servers
                controller.pulse_server_instances.add(instance_key)
                controller.remote_pulse_servers.add(service_key)
            controller.monitor_coordinator.ensure_service(service_key)
            if changed:
                controller.mpd_service.schedule_restart(controller.pulse_wakeup.set)
                self.logger.info("Remote PulseAudio server discovered: %s", name)
                controller._write_active_clients()
                controller.pulse_wakeup.set()

        def on_service_removed(
            interface: int,
            protocol: int,
            name: str,
            _service_type: str,
            _domain: str,
            _flags: int,
        ) -> None:
            """Handle removal of one PulseAudio service instance."""
            service_name = str(name)
            service_key = service_name.lower()
            self.logger.debug(
                "Avahi ItemRemove: type=%s service=%s",
                self.pulse_service_type,
                service_key,
            )
            instance_key = (int(interface), int(protocol), service_key)
            removed = False
            with controller.pulse_servers_lock:
                controller.pulse_server_instances.discard(instance_key)
                if not any(
                    item[2] == service_key
                    for item in controller.pulse_server_instances
                ):
                    removed = service_key in controller.remote_pulse_servers
                    controller.remote_pulse_servers.discard(service_key)
            if removed:
                controller.mpd_service.schedule_restart(controller.pulse_wakeup.set)
                self.logger.info("Remote PulseAudio service removed: %s", service_name)
                with controller.client_addresses_lock:
                    controller.client_addresses.pop(service_key, None)
                controller.monitor_coordinator.remove_service(service_key)
                controller._write_active_clients()
                controller.pulse_wakeup.set()

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
