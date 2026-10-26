#!/usr/bin/python3

"""Scheduling and state transitions for remote audio-service monitors."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import logging
import threading
import time
from typing import Any, Callable

from monitoring import MonitoringResult, PingMonitor, PulseAudioMonitor, SnapcastMonitor
from snapserver_service import SnapserverService


class MonitorCoordinator:
    """Coordinate device ping, PulseAudio, and Snapclient monitors.

    The coordinator owns all monitor deadlines and service-health dictionaries.
    The application controller only provides lifecycle callbacks and consumes
    the resulting state for JSON publication and audio policy decisions.
    """

    def __init__(
        self,
        snapserver_service: SnapserverService,
        discovered_addresses: Mapping[str, Iterable[str]],
        addresses_lock: threading.Lock,
        snapclient_prefix: str,
        device_ping_interval: float,
        device_ping_timeout: float,
        device_ping_failure_threshold: int,
        pulse_probe_interval: float,
        pulse_probe_timeout: float,
        pulse_probe_failure_threshold: int,
        snapcast_probe_interval: float,
        snapcast_last_seen_timeout: float,
        logger: logging.Logger,
        publish_state: Callable[[], None],
        schedule_mpd_restart: Callable[[], None],
        wakeup: Callable[[], None],
    ) -> None:
        """Configure monitor intervals, thresholds, callbacks, and state."""
        self.snapserver_service = snapserver_service
        self.discovered_addresses = discovered_addresses
        self.addresses_lock = addresses_lock
        self.snapclient_prefix = snapclient_prefix
        self.logger = logger
        self.publish_state = publish_state
        self.schedule_mpd_restart = schedule_mpd_restart
        self.wakeup = wakeup

        self.device_ping_interval = device_ping_interval
        self.device_ping_timeout = device_ping_timeout
        self.device_ping_failure_threshold = device_ping_failure_threshold
        self.pulse_probe_interval = pulse_probe_interval
        self.pulse_probe_timeout = pulse_probe_timeout
        self.pulse_probe_failure_threshold = pulse_probe_failure_threshold
        self.snapcast_probe_interval = snapcast_probe_interval
        self.snapcast_last_seen_timeout = snapcast_last_seen_timeout

        self.device_ping_monitors: dict[str, PingMonitor] = {}
        self.device_ping_due: dict[str, float] = {}
        self.device_availability: dict[str, bool] = {}
        self.pulse_monitors: dict[str, PulseAudioMonitor] = {}
        self.pulse_probe_due: dict[str, float] = {}
        self.pulse_service_active: dict[str, bool] = {}
        self.snapcast_monitors: dict[str, SnapcastMonitor] = {}
        self.snapcast_probe_due: dict[str, float] = {}
        self.snapcast_service_active: dict[str, bool] = {}
        self.snapcast_status_known: dict[str, bool] = {}
        self.service_keys_by_device: dict[str, set[str]] = {}
        self.next_check = float("inf")

    def ensure_service(self, service_name: str) -> None:
        """Create the device and service monitor associated with Avahi ItemNew."""
        service_key = str(service_name).lower()
        client_key = self._client_key(service_name)
        self.service_keys_by_device.setdefault(client_key, set()).add(service_key)
        self.device_availability.setdefault(client_key, True)
        if client_key not in self.device_ping_monitors:
            self.logger.debug("Creating device monitor: client=%s", client_key)
            self.device_ping_monitors[client_key] = PingMonitor(
                addresses=self._device_addresses(client_key),
                timeout=self.device_ping_timeout,
                failure_threshold=self.device_ping_failure_threshold,
            )
            self.device_ping_due[client_key] = 0.0

        if service_key.startswith("pulse@"):
            if service_key not in self.pulse_monitors:
                self.logger.debug(
                    "Creating PulseAudio service monitor: service=%s",
                    service_key,
                )
                self.pulse_monitors[service_key] = PulseAudioMonitor(
                    addresses=self._service_addresses(service_key),
                    timeout=self.pulse_probe_timeout,
                    failure_threshold=self.pulse_probe_failure_threshold,
                )
                self.pulse_probe_due[service_key] = 0.0
            self.pulse_service_active.setdefault(service_key, False)
            return

        if service_key.startswith(self.snapclient_prefix.lower()):
            if service_key not in self.snapcast_monitors:
                self.logger.debug(
                    "Creating Snapclient service monitor: service=%s",
                    service_key,
                )
                self.snapcast_monitors[service_key] = SnapcastMonitor(
                    last_seen_timeout=self.snapcast_last_seen_timeout,
                )
                self.snapcast_probe_due[service_key] = 0.0
            self.snapcast_service_active.setdefault(service_key, False)
            self.snapcast_status_known.setdefault(service_key, False)

    def remove_service(self, service_name: str) -> None:
        """Remove one Avahi service monitor and unused device state."""
        service_key = str(service_name).lower()
        client_key = self._client_key(service_name)
        self.logger.debug("Removing service monitor: service=%s", service_key)
        self.pulse_monitors.pop(service_key, None)
        self.pulse_probe_due.pop(service_key, None)
        self.pulse_service_active.pop(service_key, None)
        self.snapcast_monitors.pop(service_key, None)
        self.snapcast_probe_due.pop(service_key, None)
        self.snapcast_service_active.pop(service_key, None)
        self.snapcast_status_known.pop(service_key, None)

        services = self.service_keys_by_device.get(client_key)
        if services is not None:
            services.discard(service_key)
            if services:
                return
            self.service_keys_by_device.pop(client_key, None)
        self.device_ping_monitors.pop(client_key, None)
        self.device_ping_due.pop(client_key, None)
        self.device_availability.pop(client_key, None)

    def mark_snapcast_status_unknown(self, service_name: str) -> None:
        """Force a newly discovered Snapclient to await fresh status data."""
        self.snapcast_status_known[str(service_name).lower()] = False

    def reconcile(self, now: float, snapserver_active: bool) -> None:
        """Run only monitors whose individual deadlines have expired."""
        self._check_devices(now)
        self._check_pulse_services(now)
        self._check_snapcast_services(now, snapserver_active)
        due_times = [
            *self.device_ping_due.values(),
            *self.pulse_probe_due.values(),
            *self.snapcast_probe_due.values(),
        ]
        self.next_check = min(due_times, default=float("inf"))

    def _check_devices(self, now: float) -> None:
        """Run due device-level ICMP checks."""
        for client_key, monitor in tuple(self.device_ping_monitors.items()):
            due = self.device_ping_due.get(client_key, 0.0)
            if now < due:
                continue
            addresses = self._device_addresses(client_key)
            self.logger.debug(
                "Running device ping: client=%s addresses=%s",
                client_key,
                addresses,
            )
            monitor.set_addresses(addresses)
            result = monitor.check()
            self.device_ping_due[client_key] = now + self.device_ping_interval
            self._handle_device_result(client_key, result)

    def _check_pulse_services(self, now: float) -> None:
        """Run due PulseAudio native-protocol handshakes."""
        for service_key, monitor in tuple(self.pulse_monitors.items()):
            due = self.pulse_probe_due.get(service_key, 0.0)
            if now < due:
                continue
            client_key = self._client_key(service_key)
            if not self.device_availability.get(client_key, True):
                self.logger.debug(
                    "Skipping PulseAudio probe for unavailable device: %s",
                    client_key,
                )
                self.pulse_probe_due[service_key] = now + self.pulse_probe_interval
                continue
            addresses = self._service_addresses(service_key)
            self.logger.debug(
                "Running PulseAudio probe: service=%s addresses=%s",
                service_key,
                addresses,
            )
            monitor.set_addresses(addresses)
            result = monitor.check()
            self.pulse_probe_due[service_key] = now + self.pulse_probe_interval
            self._handle_service_result(service_key, result, "pulse")

    def _check_snapcast_services(self, now: float, snapserver_active: bool) -> None:
        """Run due Snapclient status checks and always schedule the next probe."""
        due_services = [
            service_key
            for service_key in self.snapcast_monitors
            if now >= self.snapcast_probe_due.get(service_key, 0.0)
        ]
        if not due_services:
            return
        if not snapserver_active:
            self.logger.debug("Deferring Snapcast status check: snapserver inactive")
            self._defer_snapcast_checks(due_services, now)
            return

        self.logger.debug("Running Snapcast status check: services=%s", due_services)
        clients = self.snapserver_service.status_clients()
        if clients is None:
            self.logger.debug(
                "Skipping Snapcast service state update: API unavailable; retrying in %.1fs",
                self.snapcast_probe_interval,
            )
            # An API error is not a successful observation. Keep the previous
            # service state, but move the deadline so the main loop waits.
            self._defer_snapcast_checks(due_services, now)
            return

        observed_at = time.time()
        for service_key in due_services:
            client_key = self._client_key(service_key)
            result = self.snapcast_monitors[service_key].observe_client(
                clients.get(client_key),
                observed_at,
            )
            self.snapcast_probe_due[service_key] = now + self.snapcast_probe_interval
            self.snapcast_status_known[service_key] = True
            self._handle_service_result(service_key, result, "snapcast")

    def _defer_snapcast_checks(self, service_keys: Iterable[str], now: float) -> None:
        """Schedule a later Snapcast probe without changing service health."""
        next_probe = now + self.snapcast_probe_interval
        for service_key in service_keys:
            self.snapcast_probe_due[service_key] = next_probe

    def _handle_device_result(
        self,
        client_key: str,
        result: MonitoringResult,
    ) -> None:
        """Apply a device ping transition to all services on that device."""
        self.logger.debug(
            "Device monitor result: client=%s available=%s changed=%s failures=%s reason=%s",
            client_key,
            result.available,
            result.changed,
            result.consecutive_failures,
            result.reason,
        )
        if not result.changed or result.available is None:
            return
        available = bool(result.available)
        previous_availability = self.device_availability.get(client_key)
        self.device_availability[client_key] = available
        if available:
            if previous_availability is True:
                return
            self.logger.info("Device available again after ICMP recovery: %s", client_key)
            for service_key, monitor in self._service_monitors_for_device(client_key):
                monitor.reset()
                if service_key.startswith("pulse@"):
                    self.pulse_service_active[service_key] = False
                    self.pulse_probe_due[service_key] = 0.0
                else:
                    self.snapcast_service_active[service_key] = False
                    self.snapcast_status_known[service_key] = False
                    self.snapserver_service.reset_presence_request()
                    self.schedule_mpd_restart()
                    self.snapcast_probe_due[service_key] = 0.0
        else:
            self.logger.warning(
                "Device unavailable after %d failed pings: %s",
                result.consecutive_failures,
                client_key,
            )
            for service_key, _monitor in self._service_monitors_for_device(client_key):
                if service_key.startswith("pulse@"):
                    self.pulse_service_active[service_key] = False
                else:
                    self.snapcast_service_active[service_key] = False
                    self.snapcast_status_known[service_key] = False
                self.schedule_mpd_restart()
        self.publish_state()
        self.wakeup()

    def _handle_service_result(
        self,
        service_key: str,
        result: MonitoringResult,
        service_type: str,
    ) -> None:
        """Apply one PulseAudio or Snapclient health transition."""
        self.logger.debug(
            "Service monitor result: service=%s type=%s available=%s changed=%s failures=%s reason=%s",
            service_key,
            service_type,
            result.available,
            result.changed,
            result.consecutive_failures,
            result.reason,
        )
        if not result.changed or result.available is None:
            return
        available = bool(result.available)
        if service_type == "pulse":
            previous = self.pulse_service_active.get(service_key, False)
            self.pulse_service_active[service_key] = available
            self.logger.info(
                "PulseAudio service %s: %s%s",
                service_key,
                "available" if available else "unavailable",
                " again" if available and not previous else "",
            )
            self.schedule_mpd_restart()
        else:
            previous = self.snapcast_service_active.get(service_key, False)
            self.snapcast_service_active[service_key] = available
            self.logger.info(
                "Snapclient %s: %s%s",
                service_key,
                "available" if available else "unavailable",
                " again" if available and not previous else "",
            )
        self.publish_state()
        self.wakeup()

    def _service_monitors_for_device(
        self,
        client_key: str,
    ) -> list[tuple[str, Any]]:
        """Return all service monitors belonging to one physical device."""
        monitors: list[tuple[str, Any]] = []
        monitors.extend(
            (service_key, monitor)
            for service_key, monitor in self.pulse_monitors.items()
            if self._client_key(service_key) == client_key
        )
        monitors.extend(
            (service_key, monitor)
            for service_key, monitor in self.snapcast_monitors.items()
            if self._client_key(service_key) == client_key
        )
        return monitors

    def _device_addresses(self, client_key: str) -> tuple[str, ...]:
        """Merge discovered and Snapserver-reported addresses for a device."""
        with self.addresses_lock:
            addresses = dict(self.discovered_addresses)
        return self.snapserver_service.addresses_for_client(client_key, addresses)

    def _service_addresses(self, service_name: str) -> tuple[str, ...]:
        """Merge discovered and Snapserver-reported addresses for a service."""
        with self.addresses_lock:
            addresses = dict(self.discovered_addresses)
        return self.snapserver_service.addresses_for_service(service_name, addresses)

    def _client_key(self, service_name: str) -> str:
        """Normalize a PulseAudio or Snapclient service name."""
        return self.snapserver_service.client_key_resolver(service_name)
