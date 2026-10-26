"""Application composition root for the event-driven audio manager."""

from __future__ import annotations

import logging
import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapters import (
    PingProbe,
    PulseAudioHandshakeProbe,
    SnapcastRpcClient,
    SystemdUnitController,
    SystemdUnitListener,
)
from .audio import (
    AudioRoutingCoordinator,
    BluetoothRouter,
    CaptureManager,
    MpdCoordinator,
    PulseAudioController,
    SnapcastAudioPipeline,
)
from .avahi import AvahiDiscovery
from .events import (
    ServiceDiscovered,
    ServiceRemoved,
    ServiceResolved,
    SystemdStateChanged,
)
from .lifecycle import SnapserverSupervisor
from .monitoring import DeviceMonitorManager, SnapcastStatusPoller
from .persistence import ActiveClientsStore
from .registry import DeviceRegistry
from .scheduler import EventLoop, MonotonicScheduler, WorkerPool


LOG = logging.getLogger("audio-manager")


@dataclass(frozen=True)
class AudioManagerConfig:
    """Runtime configuration with values suitable for the target image."""

    active_clients_path: Path = Path("/run/audio-manager/active-clients.json")
    ping_interval: float = 5.0
    ping_failure_threshold: int = 3
    pulse_interval: float = 5.0
    pulse_timeout: float = 1.0
    pulse_state_interval: float = 30.0
    snapclient_interval: float = 2.0
    snapclient_failure_threshold: int = 2
    snapclient_last_seen_max_age: float = 5.0
    systemd_fallback_interval: float = 30.0
    capture_idle_timeout: float = 60.0
    mpd_restart_debounce: float = 3.0

    @classmethod
    def from_environment(cls) -> "AudioManagerConfig":
        """Build configuration from optional ``AUDIO_MANAGER_*`` variables."""

        def number(name: str, default: float) -> float:
            raw = os.environ.get(name)
            if raw is None:
                return default
            try:
                value = float(raw)
            except ValueError:
                LOG.warning("Invalid %s=%r; using %.3f", name, raw, default)
                return default
            if value <= 0:
                LOG.warning("Invalid %s=%r; using %.3f", name, raw, default)
                return default
            return value

        def integer(name: str, default: int) -> int:
            raw = os.environ.get(name)
            if raw is None:
                return default
            try:
                value = int(raw)
            except ValueError:
                LOG.warning("Invalid %s=%r; using %d", name, raw, default)
                return default
            if value <= 0:
                LOG.warning("Invalid %s=%r; using %d", name, raw, default)
                return default
            return value

        return cls(
            active_clients_path=Path(
                os.environ.get(
                    "AUDIO_MANAGER_ACTIVE_CLIENTS_PATH",
                    str(cls.active_clients_path),
                )
            ),
            ping_interval=number("AUDIO_MANAGER_PING_INTERVAL", cls.ping_interval),
            ping_failure_threshold=integer(
                "AUDIO_MANAGER_PING_FAILURE_THRESHOLD",
                cls.ping_failure_threshold,
            ),
            pulse_interval=number("AUDIO_MANAGER_PULSE_INTERVAL", cls.pulse_interval),
            pulse_timeout=number("AUDIO_MANAGER_PULSE_TIMEOUT", cls.pulse_timeout),
            pulse_state_interval=number(
                "AUDIO_MANAGER_PULSE_STATE_INTERVAL",
                cls.pulse_state_interval,
            ),
            snapclient_interval=number(
                "AUDIO_MANAGER_SNAPCLIENT_INTERVAL",
                cls.snapclient_interval,
            ),
            snapclient_failure_threshold=integer(
                "AUDIO_MANAGER_SNAPCLIENT_FAILURE_THRESHOLD",
                cls.snapclient_failure_threshold,
            ),
            snapclient_last_seen_max_age=number(
                "AUDIO_MANAGER_SNAPCLIENT_LAST_SEEN_MAX_AGE",
                cls.snapclient_last_seen_max_age,
            ),
            systemd_fallback_interval=number(
                "AUDIO_MANAGER_SYSTEMD_FALLBACK_INTERVAL",
                cls.systemd_fallback_interval,
            ),
            capture_idle_timeout=number(
                "AUDIO_MANAGER_CAPTURE_IDLE_TIMEOUT",
                cls.capture_idle_timeout,
            ),
            mpd_restart_debounce=number(
                "AUDIO_MANAGER_MPD_RESTART_DEBOUNCE",
                cls.mpd_restart_debounce,
            ),
        )


class AudioManagerApplication:
    """Own all components and run the event-driven audio manager."""

    def __init__(self, config: AudioManagerConfig | None = None) -> None:
        self.config = config or AudioManagerConfig.from_environment()
        self.loop = EventLoop()
        self.scheduler = self.loop.scheduler
        self.workers = WorkerPool(self.loop)
        self.registry = DeviceRegistry()
        self.store = ActiveClientsStore(self.config.active_clients_path)

        self.ping_probe = PingProbe()
        self.pulse_probe = PulseAudioHandshakeProbe()
        self.snapcast_rpc = SnapcastRpcClient()
        self.snapserver_systemd = SystemdUnitController("snapserver.service")
        self.mpd_systemd = SystemdUnitController("mpd.service")

        self.monitor_manager = DeviceMonitorManager(
            self.registry,
            self.loop,
            self.scheduler,
            self.workers,
            self.ping_probe,
            self.pulse_probe,
            self._on_registry_changed,
            ping_interval=self.config.ping_interval,
            ping_failure_threshold=self.config.ping_failure_threshold,
            pulse_interval=self.config.pulse_interval,
            pulse_timeout=self.config.pulse_timeout,
            snapclient_failure_threshold=self.config.snapclient_failure_threshold,
            snapclient_last_seen_max_age=self.config.snapclient_last_seen_max_age,
        )
        self.status_poller = SnapcastStatusPoller(
            self.registry,
            self.monitor_manager,
            self.loop,
            self.scheduler,
            self.workers,
            self.snapcast_rpc,
            interval=self.config.snapclient_interval,
        )
        # All audio components must share one PulseAudio connection wrapper.
        pulse = PulseAudioController()
        self.audio = AudioRoutingCoordinator(
            pulse,
            SnapcastAudioPipeline(pulse),
            BluetoothRouter(pulse),
            CaptureManager(self.config.capture_idle_timeout),
            self.scheduler,
            reconcile_interval=self.config.pulse_state_interval,
        )
        self.mpd = MpdCoordinator(
            self.scheduler,
            self.workers,
            self.mpd_systemd,
            debounce=self.config.mpd_restart_debounce,
        )
        self.supervisor = SnapserverSupervisor(
            self.registry,
            self.loop,
            self.scheduler,
            self.workers,
            self.snapserver_systemd,
            self.status_poller,
            self.audio.set_snapserver_active,
            fallback_interval=self.config.systemd_fallback_interval,
        )
        self.avahi = AvahiDiscovery(self._post_event)
        self.systemd_listener = SystemdUnitListener("snapserver.service")
        self._stopping = False

    def _post_event(self, event: object) -> None:
        """Post a background adapter event to the main event-loop thread."""

        self.loop.post(lambda: self._handle_event(event))

    def _handle_event(self, event: object) -> None:
        """Dispatch one Avahi or systemd event."""

        if isinstance(event, ServiceDiscovered):
            self.monitor_manager.add_service(event.key, event.port)
        elif isinstance(event, ServiceResolved):
            self.monitor_manager.resolve_service(
                event.key,
                event.address,
                event.port,
            )
        elif isinstance(event, ServiceRemoved):
            self.monitor_manager.remove_service(event.key)
        elif isinstance(event, SystemdStateChanged):
            self.supervisor.on_systemd_state_changed(event.active)
        else:
            LOG.warning("Ignoring unknown application event: %r", event)

    def _on_registry_changed(self, _device_id: str) -> None:
        """Publish device state and reconcile dependent subsystems."""

        try:
            self.store.publish(self.registry.active_clients_payload())
        except OSError:
            LOG.warning("Active client state could not be published")
        self.mpd.update_topology(self.registry.devices())
        self.supervisor.on_registry_changed()

    def _on_systemd_state(self, active: bool) -> None:
        """Post a systemd state change received on the listener thread."""

        self._post_event(SystemdStateChanged("snapserver.service", active))

    def _install_signal_handlers(self) -> None:
        """Stop the event loop cleanly on SIGTERM and SIGINT."""

        def stop(_signum: int, _frame: Any) -> None:
            LOG.info("Shutdown signal received")
            self.loop.stop()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

    def run(self) -> int:
        """Start adapters and run until the service receives a stop signal."""

        self._install_signal_handlers()
        self.store.publish(self.registry.active_clients_payload())
        self.supervisor.start()
        self.audio.start()
        self.avahi.start()
        self.systemd_listener.start(self._on_systemd_state)
        LOG.info("Audio manager started")
        try:
            self.loop.run()
        finally:
            self.stop()
        return 0

    def stop(self) -> None:
        """Stop listeners, timers, workers, and local audio resources.

        This method is idempotent so it can safely be called from the normal
        event-loop shutdown path and from an exceptional cleanup path.
        """

        if self._stopping:
            return
        self._stopping = True
        LOG.info("Stopping audio manager")
        self.avahi.stop()
        self.systemd_listener.stop()
        self.supervisor.stop()
        self.monitor_manager.reset()
        self.audio.stop()
        self.workers.shutdown()
        LOG.info("Audio manager stopped")
