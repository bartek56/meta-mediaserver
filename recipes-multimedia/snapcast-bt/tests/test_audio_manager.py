"""Unit tests for the event-driven audio manager state machine."""

from __future__ import annotations

import time
from types import SimpleNamespace

from audio_manager.models import (
    HostStatus,
    ServiceKey,
    ServiceKind,
    ServiceStatus,
)
from audio_manager.audio import BluetoothRouter, PulseSnapshot
from audio_manager.monitoring import (
    DeviceMonitorManager,
    SnapcastStatusPoller,
    SnapclientObservation,
)
from audio_manager.lifecycle import SnapserverDesiredStatePolicy
from audio_manager.registry import DeviceRegistry
from audio_manager.scheduler import EventLoop, MonotonicScheduler, WorkerPool


class FakePingProbe:
    """Return a stable result without invoking the system ping binary."""

    def check(self, _address: str) -> bool:
        """Return a successful probe result."""

        return True


class FakePulseProbe:
    """Return a stable PulseAudio probe result."""

    def check(self, _address: str, _port: int, _timeout: float) -> bool:
        """Return a successful probe result."""

        return True


def test_services_share_one_device_and_remove_independently() -> None:
    """PulseAudio and Snapclient advertisements must merge by device ID."""

    registry = DeviceRegistry()
    snap_key = ServiceKey(ServiceKind.SNAPCLIENT, 1, 0, "Snapclient-room")
    pulse_key = ServiceKey(ServiceKind.PULSE_AUDIO, 1, 0, "pulse@room")

    registry.add_service(snap_key, 1704)
    registry.add_service(pulse_key, 4713)
    registry.resolve_service(snap_key, "192.0.2.10", 1704)
    registry.resolve_service(pulse_key, "192.0.2.10", 4713)

    assert len(registry.devices()) == 1
    assert registry.get("room").has_service(ServiceKind.SNAPCLIENT)  # type: ignore[union-attr]

    registry.remove_service(snap_key)

    device = registry.get("room")
    assert device is not None
    assert not device.has_service(ServiceKind.SNAPCLIENT)
    assert device.has_service(ServiceKind.PULSE_AUDIO)


def test_scheduler_uses_fixed_five_second_deadlines() -> None:
    """A periodic task should not drift with callback execution time."""

    current = [0.0]
    scheduler = MonotonicScheduler(lambda: current[0])
    calls: list[float] = []
    scheduler.call_every(5.0, lambda: calls.append(current[0]), immediate=True)

    scheduler.run_due()
    current[0] = 4.99
    scheduler.run_due()
    current[0] = 5.0
    scheduler.run_due()

    assert calls == [0.0, 5.0]


def test_snapclient_becomes_inactive_after_two_invalid_polls() -> None:
    """Two invalid status observations must clear Snapclient activity."""

    registry = DeviceRegistry()
    loop = EventLoop()
    workers = WorkerPool(loop, max_workers=1)
    manager = DeviceMonitorManager(
        registry,
        loop,
        loop.scheduler,
        workers,
        FakePingProbe(),
        FakePulseProbe(),
        lambda _device_id: None,
    )
    key = ServiceKey(ServiceKind.SNAPCLIENT, 1, 0, "Snapclient-room")
    manager.add_service(key, 1704)
    manager.resolve_service(key, "192.0.2.10", 1704)
    registry.update_host("room", HostStatus.AVAILABLE, 0)

    manager.observe_snapclient("room", SnapclientObservation(False, False, None))
    assert registry.get("room").snapclient_failure_count == 1  # type: ignore[union-attr]
    manager.observe_snapclient("room", SnapclientObservation(False, False, None))
    assert registry.get("room").snapclient_status is ServiceStatus.INACTIVE  # type: ignore[union-attr]

    manager.observe_snapclient(
        "room",
        SnapclientObservation(True, True, int(time.time())),
    )
    assert registry.get("room").snapclient_status is ServiceStatus.ACTIVE  # type: ignore[union-attr]
    workers.shutdown()


def test_snapserver_status_poller_does_not_poll_when_disabled() -> None:
    """The inactive Snapserver path must make no Server.GetStatus request."""

    class FakeRpc:
        calls = 0

        def get_status(self):
            self.calls += 1
            return {}

    registry = DeviceRegistry()
    loop = EventLoop()
    workers = WorkerPool(loop, max_workers=1)
    manager = DeviceMonitorManager(
        registry,
        loop,
        loop.scheduler,
        workers,
        FakePingProbe(),
        FakePulseProbe(),
        lambda _device_id: None,
    )
    rpc = FakeRpc()
    poller = SnapcastStatusPoller(
        registry,
        manager,
        loop,
        loop.scheduler,
        workers,
        rpc,
    )

    poller.set_enabled(False)
    loop.scheduler.run_due()

    assert rpc.calls == 0
    workers.shutdown()


def test_snapserver_stays_stopped_without_a_reachable_remote_client() -> None:
    """No discovered or ping-reachable client must request Snapserver start."""

    registry = DeviceRegistry()
    assert SnapserverDesiredStatePolicy.should_run(registry) is False

    key = ServiceKey(ServiceKind.SNAPCLIENT, 1, 0, "Snapclient-room")
    registry.add_service(key, 1704)
    registry.resolve_service(key, "192.0.2.10", 1704)
    assert SnapserverDesiredStatePolicy.should_run(registry) is False

    registry.update_host("room", HostStatus.AVAILABLE, 0)
    assert SnapserverDesiredStatePolicy.should_run(registry) is True


def test_bluetooth_loopback_volume_is_set_to_120_percent() -> None:
    """Bluetooth loopback volume must preserve the previous 120 percent gain."""

    class FakePulse:
        def __init__(self) -> None:
            self.volume_updates: list[tuple[str, float]] = []

        def modules(self):
            return ()

        def load_module(self, _name: str, _argument: str) -> int:
            return 10

        def set_loopback_volume(self, sink_name: str, gain: float) -> int:
            self.volume_updates.append((sink_name, gain))
            return 1

        def server_default_sink(self):
            return None

    pulse = FakePulse()
    router = BluetoothRouter(pulse)  # type: ignore[arg-type]
    snapshot = PulseSnapshot(
        sinks=(SimpleNamespace(name="snapcast_bt"),),
        sources=(SimpleNamespace(name="bluez_source.phone"),),
        sink_inputs=(),
    )

    router.reconcile(snapshot, snapserver_active=True)

    assert pulse.volume_updates == [("snapcast_bt", 1.2)]
