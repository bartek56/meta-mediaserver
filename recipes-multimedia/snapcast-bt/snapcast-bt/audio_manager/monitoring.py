"""Device, PulseAudio, and Snapclient monitors."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from .adapters import PingProbe, PulseAudioHandshakeProbe, SnapcastRpcClient
from .events import (
    PingCompleted,
    ProbeFailed,
    PulseProbeCompleted,
    SnapcastStatusCompleted,
)
from .models import DeviceState, HostStatus, ServiceKind, ServiceStatus
from .registry import DeviceRegistry
from .scheduler import EventLoop, MonotonicScheduler, TimerHandle, WorkerPool


LOG = logging.getLogger("audio-manager.monitoring")


@dataclass(frozen=True)
class SnapclientObservation:
    """One client's observation from a single Server.GetStatus response."""

    found: bool
    connected: bool
    last_seen_sec: int | None

    def is_active(self, now: float, max_age: float) -> bool:
        """Return whether this observation satisfies the active-client rules."""

        if not self.found or not self.connected or self.last_seen_sec is None:
            return False
        return now - self.last_seen_sec < max_age


class DeviceMonitor:
    """Monitor one device with one host monitor and one Pulse monitor."""

    def __init__(
        self,
        device_id: str,
        registry: DeviceRegistry,
        loop: EventLoop,
        scheduler: MonotonicScheduler,
        workers: WorkerPool,
        ping_probe: PingProbe,
        pulse_probe: PulseAudioHandshakeProbe,
        on_changed: Callable[[str], None],
        *,
        ping_interval: float,
        ping_failure_threshold: int,
        pulse_interval: float,
        pulse_timeout: float,
        snapclient_failure_threshold: int,
        snapclient_last_seen_max_age: float,
    ) -> None:
        self.device_id = device_id
        self._registry = registry
        self._loop = loop
        self._scheduler = scheduler
        self._workers = workers
        self._ping_probe = ping_probe
        self._pulse_probe = pulse_probe
        self._on_changed = on_changed
        self._ping_interval = ping_interval
        self._ping_failure_threshold = ping_failure_threshold
        self._pulse_interval = pulse_interval
        self._pulse_timeout = pulse_timeout
        self._snapclient_failure_threshold = snapclient_failure_threshold
        self._snapclient_last_seen_max_age = snapclient_last_seen_max_age
        self._ping_timer: TimerHandle | None = None
        self._pulse_timer: TimerHandle | None = None
        self._ping_inflight = False
        self._pulse_inflight = False
        self._address_index = 0
        self._running = True

    @property
    def state(self) -> DeviceState | None:
        """Return the current registry state for this monitor."""

        return self._registry.get(self.device_id)

    def refresh(self) -> None:
        """Reconcile timers with the current service and address state."""

        if not self._running:
            return
        state = self.state
        if state is None:
            self.stop()
            return

        ipv4_addresses = tuple(
            address for address in state.endpoints() if ":" not in address
        )
        if not ipv4_addresses:
            if self._ping_timer is not None:
                self._ping_timer.cancel()
                self._ping_timer = None
            if state.host_status is not HostStatus.WAITING_FOR_ADDRESS:
                self._registry.update_host(
                    self.device_id,
                    HostStatus.WAITING_FOR_ADDRESS,
                    0,
                )
                LOG.info("Device %s is waiting for an IPv4 address", self.device_id)
                self._on_changed(self.device_id)
            self._disable_pulse_timer()
            return

        if self._ping_timer is None or self._ping_timer.cancelled:
            self._ping_timer = self._scheduler.call_every(
                self._ping_interval,
                self._start_ping,
                immediate=True,
            )

        state = self.state
        if state is not None and state.host_status is HostStatus.AVAILABLE:
            if state.has_service(ServiceKind.PULSE_AUDIO):
                if self._pulse_timer is None or self._pulse_timer.cancelled:
                    self._pulse_timer = self._scheduler.call_every(
                        self._pulse_interval,
                        self._start_pulse_probe,
                        immediate=True,
                    )
            else:
                self._disable_pulse_timer()
        else:
            self._disable_pulse_timer()

    def _start_ping(self) -> None:
        """Submit one ping if no previous ping is still running."""

        if self._ping_inflight or not self._running:
            return
        state = self.state
        if state is None:
            return
        addresses = tuple(address for address in state.endpoints() if ":" not in address)
        if not addresses:
            return
        address = addresses[self._address_index % len(addresses)]
        self._address_index += 1
        self._ping_inflight = True
        self._workers.submit(
            self._ping_probe.check,
            address,
            on_success=lambda success: self._on_ping_result(
                PingCompleted(self.device_id, bool(success), address)
            ),
            on_error=lambda error: self._on_ping_error(address, error),
        )

    def _on_ping_result(self, result: PingCompleted) -> None:
        self._ping_inflight = False
        if not self._running or self.state is None:
            return
        state = self.state
        previous = state.host_status
        failures = 0 if result.success else state.ping_failures + 1
        if result.success:
            status = HostStatus.AVAILABLE
            LOG.debug("Ping succeeded for %s at %s", self.device_id, result.address)
        elif failures >= self._ping_failure_threshold:
            status = HostStatus.UNAVAILABLE
            LOG.warning(
                "Device %s is unavailable after %d consecutive ping failures",
                self.device_id,
                failures,
            )
        elif previous is HostStatus.AVAILABLE:
            status = HostStatus.AVAILABLE
            LOG.debug(
                "Ping failed for %s (%d/%d); retaining available state",
                self.device_id,
                failures,
                self._ping_failure_threshold,
            )
        else:
            status = HostStatus.UNKNOWN
            LOG.debug(
                "Ping failed for %s (%d/%d)",
                self.device_id,
                failures,
                self._ping_failure_threshold,
            )

        changed = self._registry.update_host(self.device_id, status, failures)
        if changed:
            if previous is not HostStatus.AVAILABLE and status is HostStatus.AVAILABLE:
                LOG.info("Device %s became available", self.device_id)
            self._on_changed(self.device_id)
        self.refresh()

    def _on_ping_error(self, address: str, error: BaseException) -> None:
        self._ping_inflight = False
        LOG.warning("Ping probe failed for %s at %s: %s", self.device_id, address, error)
        self._on_ping_result(PingCompleted(self.device_id, False, address))

    def _start_pulse_probe(self) -> None:
        """Submit one PulseAudio handshake when the host is available."""

        if self._pulse_inflight or not self._running:
            return
        state = self.state
        if state is None or state.host_status is not HostStatus.AVAILABLE:
            return
        addresses = tuple(
            address
            for address in state.endpoints(ServiceKind.PULSE_AUDIO)
            if ":" not in address
        )
        if not addresses:
            return
        address = addresses[0]
        port = state.port(ServiceKind.PULSE_AUDIO, 4713)
        self._pulse_inflight = True
        self._workers.submit(
            self._pulse_probe.check,
            address,
            port,
            self._pulse_timeout,
            on_success=lambda success: self._on_pulse_result(
                PulseProbeCompleted(self.device_id, bool(success))
            ),
            on_error=lambda error: self._on_pulse_error(error),
        )

    def _on_pulse_result(self, result: PulseProbeCompleted) -> None:
        self._pulse_inflight = False
        state = self.state
        if not self._running or state is None:
            return
        failures = 0 if result.success else state.pulse_failure_count + 1
        status = ServiceStatus.ACTIVE if result.success else ServiceStatus.INACTIVE
        if result.success:
            LOG.debug("PulseAudio handshake succeeded for %s", self.device_id)
        else:
            LOG.warning("PulseAudio is unavailable on %s", self.device_id)
        if self._registry.update_pulse(self.device_id, status, failures):
            self._on_changed(self.device_id)

    def _on_pulse_error(self, error: BaseException) -> None:
        self._pulse_inflight = False
        LOG.warning("PulseAudio probe failed for %s: %s", self.device_id, error)
        self._on_pulse_result(PulseProbeCompleted(self.device_id, False))

    def observe_snapclient(self, observation: SnapclientObservation) -> None:
        """Apply one status-poller observation for this device.

        Args:
            observation: The record corresponding to this device from one
                ``Server.GetStatus`` response.
        """

        state = self.state
        if not self._running or state is None or state.host_status is not HostStatus.AVAILABLE:
            return
        active = observation.is_active(time.time(), self._snapclient_last_seen_max_age)
        failures = 0 if active else state.snapclient_failure_count + 1
        if active:
            status = ServiceStatus.ACTIVE
            LOG.debug("Snapclient %s is active", self.device_id)
        elif failures >= self._snapclient_failure_threshold:
            status = ServiceStatus.INACTIVE
            LOG.warning(
                "Snapclient %s removed from active state after %d invalid status polls",
                self.device_id,
                failures,
            )
        elif state.snapclient_status is ServiceStatus.ACTIVE:
            status = ServiceStatus.ACTIVE
            LOG.debug(
                "Snapclient status invalid for %s (%d/%d); retaining active state",
                self.device_id,
                failures,
                self._snapclient_failure_threshold,
            )
        else:
            status = ServiceStatus.UNKNOWN
            LOG.debug(
                "Snapclient status invalid for %s (%d/%d)",
                self.device_id,
                failures,
                self._snapclient_failure_threshold,
            )
        if self._registry.update_snapclient(
            self.device_id,
            status,
            failures,
            observation.last_seen_sec,
        ):
            self._on_changed(self.device_id)

    def reset_snapclient(self) -> None:
        """Forget Snapclient probe failures after Snapserver stops."""

        if self.state is None:
            return
        if self._registry.update_snapclient(
            self.device_id,
            ServiceStatus.UNKNOWN,
            0,
            None,
        ):
            self._on_changed(self.device_id)

    def _disable_pulse_timer(self) -> None:
        if self._pulse_timer is not None:
            self._pulse_timer.cancel()
            self._pulse_timer = None

    def stop(self) -> None:
        """Cancel all timers and prevent late worker results from mutating state."""

        self._running = False
        if self._ping_timer is not None:
            self._ping_timer.cancel()
        self._disable_pulse_timer()


class DeviceMonitorManager:
    """Create exactly one :class:`DeviceMonitor` for each registry device."""

    def __init__(
        self,
        registry: DeviceRegistry,
        loop: EventLoop,
        scheduler: MonotonicScheduler,
        workers: WorkerPool,
        ping_probe: PingProbe,
        pulse_probe: PulseAudioHandshakeProbe,
        on_changed: Callable[[str], None],
        *,
        ping_interval: float = 5.0,
        ping_failure_threshold: int = 3,
        pulse_interval: float = 5.0,
        pulse_timeout: float = 1.0,
        snapclient_failure_threshold: int = 2,
        snapclient_last_seen_max_age: float = 5.0,
    ) -> None:
        self._registry = registry
        self._loop = loop
        self._scheduler = scheduler
        self._workers = workers
        self._ping_probe = ping_probe
        self._pulse_probe = pulse_probe
        self._on_changed = on_changed
        self._settings = {
            "ping_interval": ping_interval,
            "ping_failure_threshold": ping_failure_threshold,
            "pulse_interval": pulse_interval,
            "pulse_timeout": pulse_timeout,
            "snapclient_failure_threshold": snapclient_failure_threshold,
            "snapclient_last_seen_max_age": snapclient_last_seen_max_age,
        }
        self._monitors: dict[str, DeviceMonitor] = {}

    def add_service(self, key: Any, port: int) -> None:
        """Register a discovered service and refresh its device monitor."""

        change = self._registry.add_service(key, port)
        monitor = self._monitors.get(change.device_id)
        if monitor is None:
            monitor = DeviceMonitor(
                change.device_id,
                self._registry,
                self._loop,
                self._scheduler,
                self._workers,
                self._ping_probe,
                self._pulse_probe,
                self._on_changed,
                **self._settings,
            )
            self._monitors[change.device_id] = monitor
            LOG.info("Created monitor for device %s", change.device_id)
        monitor.refresh()
        self._on_changed(change.device_id)

    def resolve_service(self, key: Any, address: str, port: int) -> None:
        """Store an address and wake the corresponding device monitor."""

        change = self._registry.resolve_service(key, address, port)
        if change is None:
            LOG.debug("Ignoring resolution for an unknown service %s", key)
            return
        monitor = self._monitors.get(change.device_id)
        if monitor is not None:
            LOG.info("Resolved device %s to %s", change.device_id, address)
            monitor.refresh()
        self._on_changed(change.device_id)

    def remove_service(self, key: Any) -> None:
        """Remove one service while retaining any other service of its device."""

        change = self._registry.remove_service(key)
        if change is None:
            return
        if change.removed:
            monitor = self._monitors.pop(change.device_id, None)
            if monitor is not None:
                monitor.stop()
            LOG.info("Removed device monitor for %s", change.device_id)
        else:
            monitor = self._monitors.get(change.device_id)
            if monitor is not None:
                monitor.refresh()
            LOG.info("Removed one service from device %s", change.device_id)
        self._on_changed(change.device_id)

    def observe_snapclient(
        self,
        device_id: str,
        observation: SnapclientObservation,
    ) -> None:
        """Forward a Snapcast status observation to one device monitor."""

        monitor = self._monitors.get(device_id)
        if monitor is not None:
            monitor.observe_snapclient(observation)

    def reset_snapclients(self) -> None:
        """Reset all per-device Snapclient states when Snapserver stops."""

        for monitor in tuple(self._monitors.values()):
            monitor.reset_snapclient()

    def reset(self) -> None:
        """Stop all monitors during application shutdown."""

        for monitor in tuple(self._monitors.values()):
            monitor.stop()
        self._monitors.clear()


class SnapcastStatusPoller:
    """Poll all remote Snapclients through one local Snapcast RPC request."""

    def __init__(
        self,
        registry: DeviceRegistry,
        manager: DeviceMonitorManager,
        loop: EventLoop,
        scheduler: MonotonicScheduler,
        workers: WorkerPool,
        client: SnapcastRpcClient,
        *,
        interval: float = 2.0,
    ) -> None:
        self._registry = registry
        self._manager = manager
        self._loop = loop
        self._scheduler = scheduler
        self._workers = workers
        self._client = client
        self._interval = interval
        self._timer: TimerHandle | None = None
        self._inflight = False
        self._enabled = False

    def set_enabled(self, enabled: bool) -> None:
        """Enable polling on Snapserver activation or stop it immediately."""

        if enabled == self._enabled:
            return
        self._enabled = enabled
        if enabled:
            LOG.info("Snapcast status polling enabled")
            self._timer = self._scheduler.call_every(
                self._interval,
                self._start_request,
                immediate=True,
            )
        else:
            LOG.info("Snapcast status polling disabled")
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._inflight = False
            self._manager.reset_snapclients()

    def _start_request(self) -> None:
        """Submit one Server.GetStatus request unless one is in flight."""

        if not self._enabled or self._inflight:
            return
        self._inflight = True
        self._workers.submit(
            self._client.get_status,
            on_success=lambda status: self._on_result(
                SnapcastStatusCompleted(status)
            ),
            on_error=lambda error: self._on_error(error),
        )

    def _on_result(self, result: SnapcastStatusCompleted) -> None:
        self._inflight = False
        if not self._enabled:
            return
        observations = self._parse_observations(result.status)
        now = time.time()
        LOG.debug("Received Snapcast status for %d client(s)", len(observations))
        for device in self._registry.devices():
            if not device.has_service(ServiceKind.SNAPCLIENT):
                continue
            if device.host_status is not HostStatus.AVAILABLE:
                continue
            observation = observations.get(
                device.device_id,
                SnapclientObservation(False, False, None),
            )
            # Evaluate age at the monitor, but use this read to make the
            # current wall-clock value explicit in logs and diagnostics.
            LOG.debug(
                "Evaluating Snapclient %s at wall time %.3f",
                device.device_id,
                now,
            )
            self._manager.observe_snapclient(device.device_id, observation)

    def _on_error(self, error: BaseException) -> None:
        self._inflight = False
        if not self._enabled:
            return
        LOG.warning("Server.GetStatus failed: %s", error)
        for device in self._registry.devices():
            if not device.has_service(ServiceKind.SNAPCLIENT):
                continue
            if device.host_status is not HostStatus.AVAILABLE:
                continue
            self._manager.observe_snapclient(
                device.device_id,
                SnapclientObservation(False, False, None),
            )

    @staticmethod
    def _parse_observations(status: dict[str, Any]) -> dict[str, SnapclientObservation]:
        """Extract client observations from a Snapcast status response."""

        observations: dict[str, SnapclientObservation] = {}
        groups = status.get("result", {}).get("server", {}).get("groups", [])
        for group in groups:
            for client in group.get("clients", []):
                host = client.get("host", {})
                raw_name = str(host.get("name", "")).strip()
                if not raw_name:
                    continue
                device_id = raw_name.lower()
                if device_id.startswith("snapclient-"):
                    device_id = device_id[len("snapclient-") :]
                last_seen = client.get("lastSeen", {}).get("sec")
                try:
                    last_seen_sec = int(last_seen)
                except (TypeError, ValueError):
                    last_seen_sec = None
                observations[device_id] = SnapclientObservation(
                    found=True,
                    connected=client.get("connected") is True,
                    last_seen_sec=last_seen_sec,
                )
        return observations

    def stop(self) -> None:
        """Disable polling during application shutdown."""

        self.set_enabled(False)
