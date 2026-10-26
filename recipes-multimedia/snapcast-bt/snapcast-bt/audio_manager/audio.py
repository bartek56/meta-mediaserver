"""Local PulseAudio, Bluetooth routing, FIFO, and capture management."""

from __future__ import annotations

import logging
import os
import signal
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapters import SystemdUnitController
from .models import DeviceState, ServiceKind, ServiceStatus
from .scheduler import EventLoop, MonotonicScheduler, TimerHandle, WorkerPool


LOG = logging.getLogger("audio-manager.audio")

DEFAULT_BLUETOOTH_LOOPBACK_GAIN = 1.2


@dataclass(frozen=True)
class PulseSnapshot:
    """The local PulseAudio objects needed by the routing policy."""

    sinks: tuple[Any, ...]
    sources: tuple[Any, ...]
    sink_inputs: tuple[Any, ...]


class PulseAudioController:
    """Small wrapper around pulsectl with lazy dependency loading."""

    def __init__(self, client_name: str = "audio-manager") -> None:
        self._client_name = client_name
        self._pulse: Any | None = None

    def connect(self) -> None:
        """Connect to the local PulseAudio server if not connected."""

        if self._pulse is not None:
            return
        import pulsectl

        self._pulse = pulsectl.Pulse(self._client_name)
        LOG.info("Connected to PulseAudio")

    def close(self) -> None:
        """Close the PulseAudio connection."""

        if self._pulse is None:
            return
        try:
            self._pulse.close()
        except Exception:
            LOG.debug("PulseAudio close failed", exc_info=True)
        finally:
            self._pulse = None

    def snapshot(self) -> PulseSnapshot:
        """Return the current local sinks, sources, and sink inputs."""

        self.connect()
        assert self._pulse is not None
        return PulseSnapshot(
            sinks=tuple(self._pulse.sink_list()),
            sources=tuple(self._pulse.source_list()),
            sink_inputs=tuple(self._pulse.sink_input_list()),
        )

    def find_sink(self, name: str, snapshot: PulseSnapshot | None = None) -> Any | None:
        """Find a sink by name in the supplied or current snapshot."""

        snapshot = snapshot or self.snapshot()
        return next((sink for sink in snapshot.sinks if sink.name == name), None)

    def server_default_sink(self) -> str | None:
        """Return the current default sink name."""

        self.connect()
        assert self._pulse is not None
        return self._pulse.server_info().default_sink_name

    def modules(self) -> tuple[Any, ...]:
        """Return loaded PulseAudio modules."""

        self.connect()
        assert self._pulse is not None
        return tuple(self._pulse.module_list())

    def load_module(self, name: str, argument: str) -> int:
        """Load a PulseAudio module and return its module index."""

        self.connect()
        assert self._pulse is not None
        return int(self._pulse.module_load(name, argument))

    def unload_module(self, index: int) -> None:
        """Unload a PulseAudio module by index."""

        self.connect()
        assert self._pulse is not None
        self._pulse.module_unload(index)

    def set_loopback_volume(self, sink_name: str, gain: float) -> int:
        """Set the volume of loopback inputs connected to a sink.

        Args:
            sink_name: PulseAudio sink receiving the loopback stream.
            gain: Linear PulseAudio gain, where ``1.0`` is 100 percent.

        Returns:
            The number of loopback sink inputs whose volume was updated.
        """

        self.connect()
        assert self._pulse is not None
        sink = next((item for item in self._pulse.sink_list() if item.name == sink_name), None)
        if sink is None:
            LOG.warning("Cannot set loopback volume: sink %s was not found", sink_name)
            return 0

        loopbacks = [
            item
            for item in self._pulse.sink_input_list()
            if item.sink == sink.index and getattr(item, "driver", "") == "module-loopback.c"
        ]
        if not loopbacks:
            LOG.debug("No loopback sink input is currently attached to %s", sink_name)
            return 0

        for item in loopbacks:
            self._pulse.volume_set_all_chans(item, gain)
        LOG.debug(
            "Set %d loopback sink input(s) on %s to %.0f%%",
            len(loopbacks),
            sink_name,
            gain * 100,
        )
        return len(loopbacks)


class BluetoothRouter:
    """Route Bluetooth input either to Snapcast or to a physical sink."""

    def __init__(
        self,
        pulse: PulseAudioController,
        *,
        snapcast_sink: str = "snapcast_bt",
        loopback_latency_ms: int = 10,
    ) -> None:
        self._pulse = pulse
        self._snapcast_sink = snapcast_sink
        self._loopback_latency_ms = loopback_latency_ms
        self._source: str | None = None
        self._target: str | None = None

    def reconcile(self, snapshot: PulseSnapshot, snapserver_active: bool) -> None:
        """Make the Bluetooth loopback target match the Snapserver state."""

        source = self._find_bluetooth_source(snapshot)
        target = self._snapcast_sink if snapserver_active else self._physical_sink(snapshot)
        if source == self._source and target == self._target:
            if target is not None:
                self._pulse.set_loopback_volume(target, DEFAULT_BLUETOOTH_LOOPBACK_GAIN)
            return
        if source is None or target is None:
            self._remove_loopback()
            self._source = source
            self._target = target
            LOG.debug("Bluetooth loopback is inactive: source=%s target=%s", source, target)
            return
        self._ensure_loopback(source, target)
        self._source = source
        self._target = target
        LOG.info(
            "Bluetooth route changed: %s -> %s",
            source,
            target,
        )

    @staticmethod
    def _find_bluetooth_source(snapshot: PulseSnapshot) -> str | None:
        """Find the preferred Bluetooth input while preserving USB support."""

        preferred = (
            "bluez_source",
            "bluez_input",
            "alsa_input.usb",
        )
        source = next(
            (
                item.name
                for item in snapshot.sources
                if any(item.name.startswith(prefix) for prefix in preferred)
            ),
            None,
        )
        return source

    def _physical_sink(self, snapshot: PulseSnapshot) -> str | None:
        """Select a non-Snapcast physical sink for direct Bluetooth audio."""

        preferred = next(
            (sink.name for sink in snapshot.sinks if sink.name == "alsa_output.headphones.stereo-fallback"),
            None,
        )
        if preferred:
            return preferred
        default = self._pulse.server_default_sink()
        if default and not default.startswith("snapcast_"):
            return default
        return next(
            (sink.name for sink in snapshot.sinks if sink.name.startswith("alsa_output.")),
            None,
        )

    def _ensure_loopback(self, source: str, target: str) -> None:
        """Ensure exactly one loopback exists for the selected source."""

        modules = self._pulse.modules()
        matching = [
            module
            for module in modules
            if module.name == "module-loopback" and f"source={source}" in module.argument
        ]
        desired = f"source={source} sink={target}"
        if any(desired in module.argument for module in matching):
            self._pulse.set_loopback_volume(target, DEFAULT_BLUETOOTH_LOOPBACK_GAIN)
            return
        for module in matching:
            self._pulse.unload_module(module.index)
        self._pulse.load_module(
            "module-loopback",
            f"source={source} sink={target} latency_msec={self._loopback_latency_ms}",
        )
        time.sleep(0.2)
        self._pulse.set_loopback_volume(target, DEFAULT_BLUETOOTH_LOOPBACK_GAIN)

    def _remove_loopback(self) -> None:
        """Unload loopbacks belonging to the previously selected source."""

        if self._source is None:
            return
        for module in self._pulse.modules():
            if module.name == "module-loopback" and f"source={self._source}" in module.argument:
                self._pulse.unload_module(module.index)


class CaptureManager:
    """Start and stop ``parec`` captures with a 60-second idle timeout."""

    def __init__(self, idle_timeout: float = 60.0) -> None:
        self._idle_timeout = idle_timeout
        self._processes: dict[str, int] = {}
        self._idle_since: dict[str, float] = {}

    def reconcile(
        self,
        key: str,
        active: bool,
        sink_name: str,
        fifo_path: str,
        now: float,
    ) -> None:
        """Start an active capture or stop it after prolonged inactivity."""

        if active:
            self._idle_since.pop(key, None)
            self._start(key, sink_name, fifo_path)
            return
        if key not in self._processes:
            return
        idle_since = self._idle_since.setdefault(key, now)
        if now - idle_since >= self._idle_timeout:
            self.stop(key)
            LOG.info("Stopped idle %s capture after %.0f seconds", key, self._idle_timeout)

    def _start(self, key: str, sink_name: str, fifo_path: str) -> None:
        """Start one ``parec`` process whose stdout is connected to a FIFO."""

        process_id = self._processes.get(key)
        if process_id is not None and self._running(process_id):
            return
        try:
            process_id = os.posix_spawnp(
                "parec",
                [
                    "parec",
                    "-d",
                    f"{sink_name}.monitor",
                    "--format=s16le",
                    "--rate=48000",
                    "--channels=2",
                ],
                os.environ.copy(),
                file_actions=[
                    (os.POSIX_SPAWN_OPEN, 1, fifo_path, os.O_WRONLY, 0o666),
                ],
            )
        except OSError as exc:
            LOG.warning("Could not start %s capture: %s", key, exc)
            return
        self._processes[key] = process_id
        LOG.info("Started %s audio capture", key)

    def stop(self, key: str) -> None:
        """Stop one capture process gracefully, then forcefully if needed."""

        process_id = self._processes.pop(key, None)
        self._idle_since.pop(key, None)
        if process_id is None:
            return
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            waited_pid, _status = os.waitpid(process_id, os.WNOHANG)
        except ChildProcessError:
            waited_pid = process_id
        if waited_pid == 0 and self._running(process_id):
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            os.waitpid(process_id, 0)
        except ChildProcessError:
            pass

    def stop_all(self) -> None:
        """Stop every managed capture process."""

        for key in tuple(self._processes):
            self.stop(key)

    @staticmethod
    def _running(process_id: int) -> bool:
        try:
            os.kill(process_id, 0)
            return True
        except ProcessLookupError:
            return False


class SnapcastAudioPipeline:
    """Create stable PulseAudio sinks and FIFO paths for Snapserver."""

    def __init__(
        self,
        pulse: PulseAudioController,
        *,
        bluetooth_sink: str = "snapcast_bt",
        pc_sink: str = "snapcast_pc",
        bluetooth_fifo: Path = Path("/tmp/snapbtfifo"),
        pc_fifo: Path = Path("/tmp/snappcfifo"),
    ) -> None:
        self._pulse = pulse
        self.bluetooth_sink = bluetooth_sink
        self.pc_sink = pc_sink
        self.bluetooth_fifo = bluetooth_fifo
        self.pc_fifo = pc_fifo

    def ensure(self) -> None:
        """Ensure both null sinks and FIFO nodes exist."""

        self._ensure_sink(self.bluetooth_sink, "Snapcast_BT")
        self._ensure_sink(self.pc_sink, "Snapcast_PC")
        self._ensure_fifo(self.bluetooth_fifo)
        self._ensure_fifo(self.pc_fifo)

    def _ensure_sink(self, name: str, description: str) -> None:
        if self._pulse.find_sink(name) is None:
            self._pulse.load_module(
                "module-null-sink",
                f"sink_name={name} sink_properties=device.description={description}",
            )
            LOG.info("Created PulseAudio sink %s", name)

    @staticmethod
    def _ensure_fifo(path: Path) -> None:
        """Create a FIFO once and reject a conflicting regular file."""

        if path.exists():
            if not stat.S_ISFIFO(path.stat().st_mode):
                raise RuntimeError(f"Audio path exists but is not a FIFO: {path}")
            return
        os.mkfifo(path, 0o666)
        LOG.info("Created audio FIFO %s", path)

    @staticmethod
    def sink_active(snapshot: PulseSnapshot, sink_name: str) -> bool:
        """Return whether an uncorked sink input feeds ``sink_name``."""

        sink = next((item for item in snapshot.sinks if item.name == sink_name), None)
        if sink is None:
            return False
        return any(
            item.sink == sink.index and not item.corked
            for item in snapshot.sink_inputs
        )


class MpdCoordinator:
    """Debounce MPD restarts after the remote audio topology changes."""

    def __init__(
        self,
        scheduler: MonotonicScheduler,
        workers: WorkerPool,
        systemd: SystemdUnitController,
        *,
        debounce: float = 3.0,
    ) -> None:
        self._scheduler = scheduler
        self._workers = workers
        self._systemd = systemd
        self._debounce = debounce
        self._timer: TimerHandle | None = None
        self._signature: tuple[tuple[str, str], ...] = ()
        self._restart_inflight = False

    def update_topology(self, devices: tuple[DeviceState, ...]) -> None:
        """Schedule an MPD restart when PulseAudio or Snapclient state changes."""

        signature_items: list[tuple[str, str]] = []
        for device in devices:
            if (
                device.has_service(ServiceKind.PULSE_AUDIO)
                and device.pulse_status is ServiceStatus.ACTIVE
            ):
                signature_items.append((device.device_id, "pulse"))
            if (
                device.has_service(ServiceKind.SNAPCLIENT)
                and device.snapclient_status is ServiceStatus.ACTIVE
            ):
                signature_items.append((device.device_id, "snapclient"))
        signature = tuple(sorted(signature_items))
        if signature == self._signature:
            return
        self._signature = signature
        LOG.info("Remote audio topology changed; scheduling MPD update")
        if self._timer is not None:
            self._timer.cancel()
        self._timer = self._scheduler.call_later(self._debounce, self._restart)

    def _restart(self) -> None:
        if self._restart_inflight:
            return
        self._restart_inflight = True
        self._workers.submit(
            self._systemd.restart,
            on_success=lambda _result: self._restart_finished(),
            on_error=lambda error: self._restart_failed(error),
        )

    def _restart_finished(self) -> None:
        self._restart_inflight = False
        LOG.info("MPD restart requested after PulseAudio topology change")

    def _restart_failed(self, error: BaseException) -> None:
        self._restart_inflight = False
        LOG.warning("Could not restart MPD after PulseAudio topology change: %s", error)


class AudioRoutingCoordinator:
    """Reconcile local Bluetooth routing and idle captures periodically."""

    def __init__(
        self,
        pulse: PulseAudioController,
        pipeline: SnapcastAudioPipeline,
        router: BluetoothRouter,
        captures: CaptureManager,
        scheduler: MonotonicScheduler,
        *,
        reconcile_interval: float = 30.0,
    ) -> None:
        self._pulse = pulse
        self._pipeline = pipeline
        self._router = router
        self._captures = captures
        self._scheduler = scheduler
        self._reconcile_interval = reconcile_interval
        self._snapserver_active = False
        self._timer: TimerHandle | None = None
        self._last_error_log = 0.0

    def start(self) -> None:
        """Start the local audio reconciliation timer."""

        self._timer = self._scheduler.call_every(
            self._reconcile_interval,
            self.reconcile,
            immediate=True,
        )

    def set_snapserver_active(self, active: bool) -> None:
        """Apply a Snapserver transition and wake audio reconciliation."""

        if self._snapserver_active == active:
            return
        self._snapserver_active = active
        if active:
            LOG.info("Enabling Snapcast audio pipeline")
        else:
            LOG.info("Disabling Snapcast audio pipeline and using direct routing")
            self._captures.stop_all()
        self.reconcile()

    def reconcile(self) -> None:
        """Read local PulseAudio state and reconcile routes/captures."""

        try:
            snapshot = self._pulse.snapshot()
            if self._snapserver_active:
                self._pipeline.ensure()
            self._router.reconcile(snapshot, self._snapserver_active)
            if not self._snapserver_active:
                return
            now = time.monotonic()
            self._captures.reconcile(
                "bluetooth",
                self._pipeline.sink_active(snapshot, self._pipeline.bluetooth_sink),
                self._pipeline.bluetooth_sink,
                str(self._pipeline.bluetooth_fifo),
                now,
            )
            self._captures.reconcile(
                "pc",
                self._pipeline.sink_active(snapshot, self._pipeline.pc_sink),
                self._pipeline.pc_sink,
                str(self._pipeline.pc_fifo),
                now,
            )
        except Exception as exc:
            now = time.monotonic()
            if now - self._last_error_log >= 30.0:
                self._last_error_log = now
                LOG.warning("Local audio reconciliation failed: %s", exc)
            else:
                LOG.debug("Local audio reconciliation failed: %s", exc)

    def stop(self) -> None:
        """Stop local reconciliation and all capture processes."""

        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._captures.stop_all()
        self._pulse.close()
