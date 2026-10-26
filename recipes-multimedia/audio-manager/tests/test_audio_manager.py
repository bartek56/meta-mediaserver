"""Unit tests for the event-driven audio manager state machine."""

from __future__ import annotations

import time
from types import SimpleNamespace

from audio_manager.models import (
    DeviceState,
    HostStatus,
    ServiceRecord,
    ServiceKey,
    ServiceKind,
    ServiceStatus,
)
from audio_manager.adapters import PulseAudioEventListener
from audio_manager.audio import (
    AudioRoutingCoordinator,
    BluetoothRouter,
    MpdCoordinator,
    PulseSnapshot,
)
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


def test_pulse_event_listener_filters_routing_events() -> None:
    """Only PulseAudio object events can wake local audio reconciliation."""

    assert PulseAudioEventListener.is_relevant_event("Event 'new' on source #3")
    assert PulseAudioEventListener.is_relevant_event("Event 'change' on sink-input #4")
    assert PulseAudioEventListener.is_relevant_event("Event 'remove' on module #5")
    assert not PulseAudioEventListener.is_relevant_event("Event 'change' on sink #0")
    assert not PulseAudioEventListener.is_relevant_event("Event 'change' on server")
    assert not PulseAudioEventListener.is_relevant_event("not an event")


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


def test_unavailable_host_uses_recovery_ping_until_avahi_removes_services() -> None:
    """Slow recovery pings continue only while Avahi retains the service."""

    class FakeTimer:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    class RecordingScheduler:
        def __init__(self):
            self.calls: list[tuple[float, bool]] = []

        def call_every(self, interval, _callback, *, immediate=False):
            self.calls.append((interval, immediate))
            return FakeTimer()

    registry = DeviceRegistry()
    scheduler = RecordingScheduler()
    manager = DeviceMonitorManager(
        registry,
        EventLoop(),
        scheduler,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        FakePingProbe(),
        FakePulseProbe(),
        lambda _device_id: None,
        ping_interval=5.0,
        recovery_ping_interval=30.0,
    )
    key = ServiceKey(ServiceKind.SNAPCLIENT, 1, 0, "Snapclient-room")
    manager.add_service(key, 1704)
    manager.resolve_service(key, "192.0.2.10", 1704)
    assert scheduler.calls == [(5.0, True)]

    registry.update_host("room", HostStatus.UNAVAILABLE, 3)
    monitor = manager._monitors["room"]  # type: ignore[attr-defined]
    monitor.refresh()
    assert scheduler.calls == [(5.0, True), (30.0, False)]

    manager.remove_service(key)
    assert monitor._running is False  # type: ignore[attr-defined]


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
    router.reconcile(snapshot, snapserver_active=True)

    assert pulse.volume_updates == [("snapcast_bt", 1.2)]


def test_bluetooth_restores_the_stream_selected_before_disconnect() -> None:
    """Disconnecting Bluetooth restores the previous PC/MPD stream."""

    class FakePulse:
        def snapshot(self):
            return PulseSnapshot((), (), ())

        def close(self):
            pass

    class FakePipeline:
        bluetooth_sink = "snapcast_bt"
        pc_sink = "snapcast_pc"
        bluetooth_fifo = "/tmp/snapbtfifo"
        pc_fifo = "/tmp/snappcfifo"

        def ensure(self):
            pass

        def sink_active(self, _snapshot, sink_name):
            return sink_name == self.pc_sink

    class FakeRouter:
        def __init__(self):
            self.states = iter((False, True, False))

        def reconcile(self, _snapshot, _snapserver_active):
            return next(self.states)

    class FakeCaptures:
        def stop_all(self):
            pass

        def reconcile(self, *_args):
            pass

    streams: list[str] = []
    coordinator = AudioRoutingCoordinator(
        FakePulse(),  # type: ignore[arg-type]
        FakePipeline(),  # type: ignore[arg-type]
        FakeRouter(),  # type: ignore[arg-type]
        FakeCaptures(),  # type: ignore[arg-type]
        MonotonicScheduler(),
        on_stream_changed=streams.append,
    )

    coordinator.set_snapserver_active(True)
    coordinator.reconcile()
    coordinator.reconcile()

    assert streams == ["PC", "Bluetooth", "PC"]


def test_active_device_removal_triggers_mpd_update_from_active_state() -> None:
    """A stale MPD output is removed when the active state loses a device."""

    class FakeTimer:
        def cancel(self):
            pass

    class FakeScheduler:
        def __init__(self):
            self.calls = 0

        def call_later(self, _delay, _callback):
            self.calls += 1
            return FakeTimer()

    class FakeWorkers:
        def submit(self, *_args, **_kwargs):
            pass

    class FakeSystemd:
        def restart(self):
            pass

    scheduler = FakeScheduler()
    coordinator = MpdCoordinator(
        scheduler,  # type: ignore[arg-type]
        FakeWorkers(),  # type: ignore[arg-type]
        FakeSystemd(),  # type: ignore[arg-type]
    )
    service_key = ServiceKey(ServiceKind.PULSE_AUDIO, 1, 0, "pulse@Office")
    device = DeviceState(
        device_id="office",
        display_name="Office",
        hostname="office.local",
        services={service_key: ServiceRecord(service_key, 4713, {"192.0.2.10"})},
        host_status=HostStatus.AVAILABLE,
        pulse_status=ServiceStatus.ACTIVE,
    )
    coordinator.update_topology((device,))

    device.host_status = HostStatus.UNAVAILABLE
    device.pulse_status = ServiceStatus.UNKNOWN
    coordinator.update_topology((device,))

    assert scheduler.calls == 2
