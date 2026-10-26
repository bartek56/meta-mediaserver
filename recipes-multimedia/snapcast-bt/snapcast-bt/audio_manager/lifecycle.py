"""Snapserver lifecycle policy and systemd state reconciliation."""

from __future__ import annotations

import logging
from typing import Callable

from .adapters import SystemdUnitController
from .models import HostStatus, ServiceKind
from .monitoring import SnapcastStatusPoller
from .registry import DeviceRegistry
from .scheduler import EventLoop, MonotonicScheduler, TimerHandle, WorkerPool


LOG = logging.getLogger("audio-manager.lifecycle")


class SnapserverDesiredStatePolicy:
    """Calculate whether remote Snapclient presence requires Snapserver."""

    @staticmethod
    def should_run(registry: DeviceRegistry) -> bool:
        """Return true for at least one discovered and ping-reachable client."""

        return any(
            device.has_service(ServiceKind.SNAPCLIENT)
            and device.host_status is HostStatus.AVAILABLE
            for device in registry.devices()
        )


class SnapserverSupervisor:
    """Coordinate desired Snapserver state, D-Bus events, and status polling."""

    def __init__(
        self,
        registry: DeviceRegistry,
        loop: EventLoop,
        scheduler: MonotonicScheduler,
        workers: WorkerPool,
        systemd: SystemdUnitController,
        status_poller: SnapcastStatusPoller,
        on_state_changed: Callable[[bool], None],
        *,
        fallback_interval: float = 30.0,
    ) -> None:
        self._registry = registry
        self._loop = loop
        self._scheduler = scheduler
        self._workers = workers
        self._systemd = systemd
        self._status_poller = status_poller
        self._on_state_changed = on_state_changed
        self._fallback_interval = fallback_interval
        self._active: bool | None = None
        self._desired: bool | None = None
        self._command_inflight = False
        self._fallback_inflight = False
        self._fallback_timer: TimerHandle | None = None

    @property
    def active(self) -> bool:
        """Return the last known systemd ActiveState."""

        return self._active is True

    def start(self) -> None:
        """Start the 30-second fallback state check immediately."""

        self._fallback_timer = self._scheduler.call_every(
            self._fallback_interval,
            self._start_fallback_read,
            immediate=True,
        )

    def on_registry_changed(self) -> None:
        """Re-evaluate the start/stop decision after a device state change."""

        self.reconcile()

    def on_systemd_state_changed(self, active: bool) -> None:
        """Apply an ActiveState event received from systemd D-Bus."""

        previous = self._active
        self._active = active
        self._status_poller.set_enabled(active)
        if previous is not active:
            LOG.info("Snapserver ActiveState changed to %s", "active" if active else "inactive")
            self._on_state_changed(active)
        self.reconcile()

    def reconcile(self) -> None:
        """Request a state transition only when desired and actual state differ."""

        desired = SnapserverDesiredStatePolicy.should_run(self._registry)
        if desired != self._desired:
            LOG.info(
                "Snapserver desired state changed to %s",
                "running" if desired else "stopped",
            )
            self._desired = desired
        if self._active is None or self._command_inflight:
            return
        if desired and not self._active:
            self._request_start()
        elif not desired and self._active:
            self._request_stop()

    def _request_start(self) -> None:
        if self._command_inflight:
            return
        self._command_inflight = True
        LOG.info("Starting snapserver.service: an available remote Snapclient exists")
        self._workers.submit(
            self._systemd.start,
            on_success=lambda _result: self._on_command_finished("start"),
            on_error=lambda error: self._on_command_failed("start", error),
        )

    def _request_stop(self) -> None:
        if self._command_inflight:
            return
        self._command_inflight = True
        LOG.info("Stopping snapserver.service: no available remote Snapclient exists")
        self._workers.submit(
            self._systemd.stop,
            on_success=lambda _result: self._on_command_finished("stop"),
            on_error=lambda error: self._on_command_failed("stop", error),
        )

    def _on_command_finished(self, command: str) -> None:
        self._command_inflight = False
        LOG.debug("systemd %s request completed", command)
        # The D-Bus PropertiesChanged signal remains authoritative.  The
        # fallback timer will also repair state if that signal was lost.

    def _on_command_failed(self, command: str, error: BaseException) -> None:
        self._command_inflight = False
        LOG.warning("Could not %s snapserver.service: %s", command, error)

    def _start_fallback_read(self) -> None:
        """Read systemd state as a 30-second safety net."""

        if self._fallback_inflight:
            LOG.debug("Skipping fallback systemd read because one is still running")
            return
        self._fallback_inflight = True
        self._workers.submit(
            self._systemd.active,
            on_success=lambda active: self._on_fallback_result(bool(active)),
            on_error=lambda error: self._on_fallback_error(error),
        )

    def _on_fallback_result(self, active: bool) -> None:
        self._fallback_inflight = False
        LOG.debug("Fallback systemd state read: %s", "active" if active else "inactive")
        self.on_systemd_state_changed(active)

    def _on_fallback_error(self, error: BaseException) -> None:
        self._fallback_inflight = False
        LOG.warning("Fallback systemd state read failed: %s", error)

    def stop(self) -> None:
        """Stop fallback checks and status polling."""

        if self._fallback_timer is not None:
            self._fallback_timer.cancel()
            self._fallback_timer = None
        self._status_poller.stop()
