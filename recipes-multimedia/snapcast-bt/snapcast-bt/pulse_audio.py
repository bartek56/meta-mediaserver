#!/usr/bin/python3

"""PulseAudio, Bluetooth routing, and FIFO capture components."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
import signal
import stat
import threading
import time
from typing import Any

import pulsectl


@dataclass(frozen=True)
class PulseAudioSnapshot:
    """Cached PulseAudio object lists used by one reconciliation pass."""

    sinks: list[Any]
    sources: list[Any]
    sink_inputs: list[Any]


@dataclass(frozen=True)
class PulseAudioActivity:
    """Derived audio activity used by the source-selection policy."""

    bluetooth_source: str | None
    bluetooth_sink_active: bool
    pc_sink_active: bool


class BluetoothRoute:
    """Keep the Bluetooth source looped to the selected PulseAudio sink."""

    def __init__(
        self,
        pulse: Any,
        direct_sink: str,
        default_gain: float,
        logger: logging.Logger,
    ) -> None:
        """Configure Bluetooth loopback routing for one PulseAudio client."""
        self.pulse = pulse
        self.direct_sink = direct_sink
        self.default_gain = default_gain
        self.logger = logger
        self.current_source: str | None = None
        self.current_target: str | None = None
        self.loopback_id: int | None = None

    def reconcile(self, source_name: str | None, target_sink: str | None) -> None:
        """Ensure the Bluetooth source is connected to the desired sink."""
        self.logger.debug(
            "Bluetooth route decision: source=%s target=%s current_source=%s current_target=%s",
            source_name,
            target_sink,
            self.current_source,
            self.current_target,
        )
        if source_name == self.current_source and target_sink == self.current_target:
            return
        if source_name is None:
            self.remove()
        elif target_sink is not None:
            self._ensure_loopback(source_name, target_sink)
        self.current_source = source_name
        self.current_target = target_sink

    def remove(self) -> None:
        """Unload loopbacks belonging to the currently tracked Bluetooth source."""
        if self.current_source is None:
            return
        self.logger.debug("Removing Bluetooth loopback: source=%s", self.current_source)
        for module in self.pulse.module_list():
            if (
                module.name == "module-loopback"
                and f"source={self.current_source}" in module.argument
            ):
                self.pulse.module_unload(module.index)
        self.loopback_id = None

    def close(self) -> None:
        """Release the Bluetooth loopback during application shutdown."""
        self.remove()

    def _ensure_loopback(self, source_name: str, target_sink: str) -> None:
        """Create or retarget the low-latency PulseAudio loopback module."""
        desired_argument = f"source={source_name} sink={target_sink}"
        modules = [
            module for module in self.pulse.module_list()
            if module.name == "module-loopback"
            and f"source={source_name}" in module.argument
        ]
        matching = next(
            (module for module in modules if desired_argument in module.argument),
            None,
        )
        if matching is not None:
            self.loopback_id = int(matching.index)
            return

        for module in modules:
            self.pulse.module_unload(module.index)
        self.loopback_id = int(
            self.pulse.module_load(
                "module-loopback",
                f"source={source_name} sink={target_sink} latency_msec=10",
            )
        )
        self.logger.info("Bluetooth route: %s -> %s", source_name, target_sink)
        time.sleep(0.2)
        self._set_loopback_volume(target_sink)

    def _set_loopback_volume(self, sink_name: str) -> None:
        """Apply the configured gain to the newly-created loopback input."""
        sink = self._find_sink(sink_name)
        if sink is None:
            return
        inputs = [
            item for item in self.pulse.sink_input_list()
            if item.sink == sink.index
        ]
        if inputs:
            self.pulse.volume_set_all_chans(
                max(inputs, key=lambda item: item.index),
                self.default_gain,
            )

    def _find_sink(self, name: str, sinks: list[Any] | None = None) -> Any | None:
        """Find one sink by its stable PulseAudio name."""
        if sinks is None:
            sinks = self.pulse.sink_list()
        return next((sink for sink in sinks if sink.name == name), None)


class CaptureProcessManager:
    """Own the lifecycle of Bluetooth and PC `parec` FIFO readers."""

    def __init__(self, idle_timeout: float, logger: logging.Logger) -> None:
        """Configure idle shutdown timing and capture process bookkeeping."""
        self.idle_timeout = idle_timeout
        self.logger = logger
        self.processes: dict[str, int] = {}
        self.idle_since: dict[str, float | None] = {"bt": None, "pc": None}

    def ensure_capture(self, key: str, sink_name: str, fifo_path: str) -> None:
        """Start one `parec` reader unless its process is already running."""
        process_id = self.processes.get(key)
        if process_id is not None and self._process_running(process_id):
            self.logger.debug("Capture already running: key=%s pid=%s", key, process_id)
            return
        try:
            process_id = os.posix_spawnp(
                "parec",
                [
                    "parec", "-d", f"{sink_name}.monitor",
                    "--format=s16le", "--rate=48000", "--channels=2",
                ],
                os.environ.copy(),
                file_actions=[
                    # A blocking FIFO open rendezvous with Snapserver's reader.
                    (os.POSIX_SPAWN_OPEN, 1, fifo_path, os.O_WRONLY, 0o666),
                ],
            )
        except OSError as exc:
            self.logger.warning("Could not start %s capture: %s", sink_name, exc)
            return
        self.processes[key] = process_id
        self.logger.info("Started audio capture for %s", sink_name)

    def stop_after_idle(self, key: str, sink_name: str, now: float) -> None:
        """Stop a capture after the configured period without active audio."""
        if key not in self.processes:
            return
        if self.idle_since[key] is None:
            self.idle_since[key] = now
        elif now - self.idle_since[key] >= self.idle_timeout:
            self.stop(key)
            self.logger.info(
                "Stopped idle audio capture for %s after %.0fs",
                sink_name,
                self.idle_timeout,
            )

    def stop_all(self) -> None:
        """Stop all currently tracked capture processes."""
        self.logger.debug("Stopping all capture processes: keys=%s", tuple(self.processes))
        for key in tuple(self.processes):
            self.stop(key)

    def stop(self, key: str) -> None:
        """Terminate one capture gracefully, then forcefully if necessary."""
        process_id = self.processes.pop(key, None)
        if process_id is None or not self._process_running(process_id):
            return
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and self._process_running(process_id):
            time.sleep(0.1)
        if self._process_running(process_id):
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self._reap_process(process_id)

    @staticmethod
    def _process_running(process_id: int) -> bool:
        """Return whether a process identifier still exists."""
        try:
            os.kill(process_id, 0)
            return True
        except ProcessLookupError:
            return False

    @staticmethod
    def _reap_process(process_id: int) -> None:
        """Collect a child process when the operating system permits it."""
        try:
            os.waitpid(process_id, 0)
        except ChildProcessError:
            pass


class PulseAudioRouter:
    """Coordinate PulseAudio snapshots, sinks, Bluetooth, and FIFO captures."""

    def __init__(
        self,
        sink_bt: str,
        sink_pc: str,
        fifo_bt: str,
        fifo_pc: str,
        direct_sink: str,
        capture_idle_timeout: float,
        default_gain: float,
        logger: logging.Logger,
        pulse: Any | None = None,
    ) -> None:
        """Create the PulseAudio routing components and their shared client."""
        self.pulse = pulse if pulse is not None else pulsectl.Pulse("audio-manager")
        self.sink_bt = sink_bt
        self.sink_pc = sink_pc
        self.fifo_bt = fifo_bt
        self.fifo_pc = fifo_pc
        self.logger = logger
        self.bluetooth = BluetoothRoute(
            self.pulse,
            direct_sink,
            default_gain,
            logger,
        )
        self.captures = CaptureProcessManager(capture_idle_timeout, logger)

    def start_event_listener(
        self,
        stop_event: threading.Event,
        wakeup: threading.Event,
    ) -> None:
        """Start the event-driven PulseAudio listener in a daemon thread."""
        thread = threading.Thread(
            target=self._event_listener,
            args=(stop_event, wakeup),
            name="pulse-events",
            daemon=True,
        )
        thread.start()

    def snapshot(self) -> PulseAudioSnapshot:
        """Read sinks, sources, and sink-inputs for one policy evaluation."""
        snapshot = PulseAudioSnapshot(
            sinks=self.pulse.sink_list(),
            sources=self.pulse.source_list(),
            sink_inputs=self.pulse.sink_input_list(),
        )
        self.logger.debug(
            "PulseAudioRouter snapshot: sinks=%d sources=%d sink_inputs=%d",
            len(snapshot.sinks),
            len(snapshot.sources),
            len(snapshot.sink_inputs),
        )
        return snapshot

    def inspect_activity(self, snapshot: PulseAudioSnapshot) -> PulseAudioActivity:
        """Find Bluetooth presence and active PC/Bluetooth sink inputs."""
        bluetooth_source = next(
            (
                source.name
                for source in snapshot.sources
                if source.name.startswith("bluez_source")
            ),
            None,
        )
        activity = PulseAudioActivity(
            bluetooth_source=bluetooth_source,
            bluetooth_sink_active=self.sink_audio_active(
                self.sink_bt,
                snapshot.sinks,
                snapshot.sink_inputs,
            ),
            pc_sink_active=self.sink_audio_active(
                self.sink_pc,
                snapshot.sinks,
                snapshot.sink_inputs,
            ),
        )
        self.logger.debug("PulseAudio activity: %s", activity)
        return activity

    def ensure_snapcast_paths(self) -> None:
        """Create the two null sinks and two FIFOs required by Snapcast."""
        self.logger.debug(
            "Ensuring Snapcast PulseAudio paths: sinks=(%s,%s) fifos=(%s,%s)",
            self.sink_bt,
            self.sink_pc,
            self.fifo_bt,
            self.fifo_pc,
        )
        self._ensure_null_sink(self.sink_bt, "Snapcast_BT")
        self._ensure_null_sink(self.sink_pc, "Snapcast_PC")
        self._ensure_fifo(self.fifo_bt)
        self._ensure_fifo(self.fifo_pc)

    def reconcile_bluetooth(
        self,
        source_name: str | None,
        snapserver_active: bool,
        sinks: list[Any],
    ) -> None:
        """Select direct or Snapcast Bluetooth routing from server state."""
        target = self.sink_bt if snapserver_active else self.physical_sink_name(sinks)
        self.bluetooth.reconcile(source_name, target)

    def reconcile_captures(
        self,
        snapserver_active: bool,
        bt_active: bool,
        pc_active: bool,
        now: float,
    ) -> None:
        """Start active captures and stop inactive/idle FIFO readers."""
        if not snapserver_active:
            self.logger.debug("Snapserver inactive: capture reconciliation stops captures")
            self.captures.stop_all()
            return
        self.logger.debug(
            "Capture decision: snapserver=%s bluetooth=%s pc=%s",
            snapserver_active,
            bt_active,
            pc_active,
        )
        if bt_active:
            self.captures.idle_since["bt"] = None
            self.captures.ensure_capture("bt", self.sink_bt, self.fifo_bt)
        else:
            self.captures.stop_after_idle("bt", self.sink_bt, now)
        if pc_active:
            self.captures.idle_since["pc"] = None
            self.captures.ensure_capture("pc", self.sink_pc, self.fifo_pc)
        else:
            self.captures.stop_after_idle("pc", self.sink_pc, now)

    def sink_audio_active(
        self,
        sink_name: str,
        sinks: list[Any],
        sink_inputs: list[Any],
    ) -> bool:
        """Return whether a sink has at least one non-corked input."""
        sink = self._find_sink(sink_name, sinks)
        if sink is None:
            return False
        return any(
            item.sink == sink.index and not item.corked
            for item in sink_inputs
        )

    def physical_sink_name(self, sinks: list[Any] | None = None) -> str | None:
        """Find the physical sink used when Snapserver is disabled."""
        sink = self._find_sink(self.bluetooth.direct_sink, sinks)
        if sink is not None:
            return sink.name
        default_name = self.pulse.server_info().default_sink_name
        if default_name and not default_name.startswith("snapcast_"):
            return default_name
        if sinks is None:
            sinks = self.pulse.sink_list()
        return next(
            (sink.name for sink in sinks if sink.name.startswith("alsa_output.")),
            None,
        )

    def close(self) -> None:
        """Stop captures, remove Bluetooth routing, and close PulseAudio."""
        self.captures.stop_all()
        self.bluetooth.close()
        try:
            self.pulse.close()
        except Exception:
            pass

    def _event_listener(
        self,
        stop_event: threading.Event,
        wakeup: threading.Event,
    ) -> None:
        """Wait for PulseAudio events and wake the controller on relevant ones."""
        while not stop_event.is_set():
            try:
                with pulsectl.Pulse("bt-snapcast-events") as pulse:
                    pulse.event_mask_set("all")

                    def on_event(event: Any) -> None:
                        """Wake the controller for PulseAudio state changes."""
                        facility = str(getattr(event, "facility", ""))
                        if facility in {
                            "sink-input", "source", "sink", "card", "module", "server",
                        }:
                            wakeup.set()

                    pulse.event_callback_set(on_event)
                    pulse.event_listen()
            except Exception as exc:
                if not stop_event.is_set():
                    self.logger.warning(
                        "PulseAudio event listener unavailable: %s",
                        exc,
                    )
                    stop_event.wait(2.0)

    def _find_sink(self, name: str, sinks: list[Any] | None = None) -> Any | None:
        """Find a PulseAudio sink by name for routing/path management."""
        if sinks is None:
            sinks = self.pulse.sink_list()
        return next((sink for sink in sinks if sink.name == name), None)

    def _ensure_null_sink(self, sink_name: str, description: str) -> None:
        """Load a null sink only when the requested sink does not exist."""
        if self._find_sink(sink_name) is None:
            self.logger.info("Creating PulseAudio null sink: %s (%s)", sink_name, description)
            self.pulse.module_load(
                "module-null-sink",
                f"sink_name={sink_name} sink_properties=device.description={description}",
            )

    @staticmethod
    def _ensure_fifo(path: str) -> None:
        """Ensure a path exists as a named pipe rather than a regular file."""
        if os.path.exists(path) and not stat.S_ISFIFO(os.stat(path).st_mode):
            # The path is owned by this component and must remain a FIFO.
            os.unlink(path)
        if not os.path.exists(path):
            os.mkfifo(path)
