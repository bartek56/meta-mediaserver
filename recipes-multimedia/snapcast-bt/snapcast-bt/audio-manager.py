#!/usr/bin/python3

"""Manage Bluetooth audio routing and Snapcast client presence.

The controller deliberately keeps running when snapserver.service is stopped.
PulseAudio is controlled through pulsectl, snapserver state through systemd's
D-Bus API, MPD through python-mpd2, and Snapcast through its JSON-RPC socket.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import signal
import socket
import threading
import time
from typing import Any

from client_state import ActiveClientsStore
from mpd_control import MpdService
from monitor_coordinator import MonitorCoordinator
from pulse_audio import PulseAudioRouter, PulseAudioSnapshot
from snapserver_service import SnapserverService
from service_discovery import ServiceDiscovery


LOG = logging.getLogger("bt-snapcast")
_configured_log_level = os.environ.get("AUDIO_MANAGER_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _configured_log_level, logging.INFO),
    format="[BT-SNAPCAST] %(levelname)s %(message)s",
)
logging.getLogger("mpd").setLevel(logging.WARNING)

SINK_BT = "snapcast_bt"
SINK_PC = "snapcast_pc"
DIRECT_SINK = "alsa_output.headphones.stereo-fallback"
FIFO_BT = "/tmp/snapbtfifo"
FIFO_PC = "/tmp/snappcfifo"
STATE_DIR = Path("/run/bt-snapcast")
ACTIVE_CLIENTS_PATH = Path("/run/audio-manager/active-clients.json")

SNAPCAST_HOST = "127.0.0.1"
SNAPCAST_PORT = 1705
SNAPCAST_STREAM_MPD = "MPD"
SNAPCAST_STREAM_BT = "Bluetooth"
SNAPCAST_STREAM_PC = "PC"
SNAPCLIENT_SERVICE_TYPE = "_snapclient._tcp"
SNAPCLIENT_SERVICE_PREFIX = "Snapclient-"
PULSE_SERVER_SERVICE_TYPE = "_pulse-server._tcp"

CAPTURE_IDLE_TIMEOUT = 60.0
PULSE_SNAPSHOT_INTERVAL = 10.0
MPD_CHECK_INTERVAL = 5.0
SNAPCAST_SYNC_INTERVAL = 5.0
SYSTEMD_STATE_FALLBACK_INTERVAL = 30.0
DEFAULT_GAIN = 1.2
MPD_RESTART_DEBOUNCE = 3.0


class Controller:
    """Coordinate discovery, health monitoring, routing policy, and timers.

    The controller does not implement the individual audio protocols. Those
    responsibilities live in the dedicated PulseAudio, MPD, Snapcast, and
    discovery components. This class owns the application state machine.
    """

    def __init__(self) -> None:
        """Create all components and initialize timer/state containers."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.stop_event = threading.Event()
        self.pulse_wakeup = threading.Event()
        self.active_client_store = ActiveClientsStore(
            ACTIVE_CLIENTS_PATH,
            SNAPCLIENT_SERVICE_PREFIX,
            LOG,
        )
        self.pulse_router = PulseAudioRouter(
            SINK_BT,
            SINK_PC,
            FIFO_BT,
            FIFO_PC,
            DIRECT_SINK,
            CAPTURE_IDLE_TIMEOUT,
            DEFAULT_GAIN,
            LOG,
        )
        self.snapserver_service = SnapserverService(
            SNAPCAST_HOST,
            SNAPCAST_PORT,
            {
                "bluetooth": SNAPCAST_STREAM_BT,
                "pc": SNAPCAST_STREAM_PC,
                "mpd": SNAPCAST_STREAM_MPD,
            },
            self._client_key_from_service,
            SYSTEMD_STATE_FALLBACK_INTERVAL,
            SNAPCAST_SYNC_INTERVAL,
            LOG,
            self.pulse_wakeup.set,
            self._on_snapserver_state_changed,
        )
        self.mpd_service = MpdService(
            "127.0.0.1",
            6600,
            LOG,
            check_interval=MPD_CHECK_INTERVAL,
            restart_debounce=MPD_RESTART_DEBOUNCE,
        )
        self.next_pulse_snapshot = 0.0
        self.cached_pulse_snapshot: PulseAudioSnapshot | None = None
        self.systemd_loop: Any | None = None
        self.remote_snapclients: set[str] = set()
        self.remote_clients_lock = threading.Lock()
        self.local_snapclient_service = f"{SNAPCLIENT_SERVICE_PREFIX}{socket.gethostname()}"
        self.remote_pulse_servers: set[str] = set()
        self.pulse_server_instances: set[tuple[int, int, str]] = set()
        self.pulse_servers_lock = threading.Lock()
        self.client_addresses: dict[str, set[str]] = {}
        self.client_addresses_lock = threading.Lock()
        self.monitor_coordinator = MonitorCoordinator(
            self.snapserver_service,
            self.client_addresses,
            self.client_addresses_lock,
            SNAPCLIENT_SERVICE_PREFIX,
            device_ping_interval=5.0,
            device_ping_timeout=1.0,
            device_ping_failure_threshold=3,
            pulse_probe_interval=5.0,
            pulse_probe_timeout=1.0,
            pulse_probe_failure_threshold=1,
            snapcast_probe_interval=2.0,
            snapcast_last_seen_timeout=5.0,
            logger=LOG,
            publish_state=self._write_active_clients,
            schedule_mpd_restart=lambda: self.mpd_service.schedule_restart(
                self.pulse_wakeup.set
            ),
            wakeup=self.pulse_wakeup.set,
        )
        self.service_discovery = ServiceDiscovery(
            self,
            SNAPCLIENT_SERVICE_TYPE,
            PULSE_SERVER_SERVICE_TYPE,
            LOG,
        )
        self._write_active_clients()

    @staticmethod
    def _client_id_from_service(service_name: str, prefix: str) -> str:
        """Remove a service-name prefix while preserving the client casing."""
        value = str(service_name)
        if value.lower().startswith(prefix.lower()):
            return value[len(prefix):]
        return value

    @classmethod
    def _client_key_from_service(cls, service_name: str) -> str:
        """Return the normalized device key shared by Pulse and Snap services."""
        value = str(service_name)
        if value.lower().startswith("pulse@"):
            return cls._client_id_from_service(value, "pulse@").lower()
        return cls._client_id_from_service(value, SNAPCLIENT_SERVICE_PREFIX).lower()

    def _start_service_resolution(
        self,
        bus: Any,
        avahi: Any,
        interface: int,
        protocol: int,
        service_name: str,
        service_type: str,
        domain: str,
    ) -> None:
        """Resolve an Avahi service and add its address to the runtime registry."""
        try:
            resolver_path = avahi.ServiceResolverNew(
                int(interface),
                int(protocol),
                service_name,
                service_type,
                domain,
                -1,
                0,
            )
            LOG.debug(
                "Started Avahi resolver: service=%s type=%s path=%s",
                service_name,
                service_type,
                resolver_path,
            )
        except dbus.DBusException as exc:
            LOG.debug("Could not create Avahi resolver for %s: %s", service_name, exc)
            return

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
            """Store the resolver address and publish the updated state."""
            with self.client_addresses_lock:
                self.client_addresses.setdefault(service_name.lower(), set()).add(
                    str(address)
                )
            LOG.debug(
                "Avahi resolver result: service=%s address=%s port=%s",
                service_name,
                address,
                port,
            )
            self._write_active_clients()
            bus.remove_signal_receiver(
                on_found,
                dbus_interface="org.freedesktop.Avahi.ServiceResolver",
                signal_name="Found",
                path=resolver_path,
            )

        bus.add_signal_receiver(
            on_found,
            dbus_interface="org.freedesktop.Avahi.ServiceResolver",
            signal_name="Found",
            path=resolver_path,
        )

    def _write_active_clients(self) -> None:
        """Publish the current discovered-service health to the state store."""
        with self.remote_clients_lock:
            snapclients = tuple(self.remote_snapclients)
        with self.pulse_servers_lock:
            pulse_servers = tuple(self.remote_pulse_servers)
        with self.client_addresses_lock:
            addresses = {
                key: sorted(values)
                for key, values in self.client_addresses.items()
            }
        snapclient_addresses = self.snapserver_service.client_addresses()
        self.active_client_store.write(
            snapclients,
            pulse_servers,
            addresses,
            snapclient_addresses,
            self.monitor_coordinator.device_availability,
            self.monitor_coordinator.snapcast_service_active,
            self.monitor_coordinator.pulse_service_active,
        )

    def start(self) -> None:
        """Start listeners and run the event/timer-driven reconciliation loop."""
        LOG.info(
            "Starting audio-manager: ping=%ss/%s failures, PulseAudio=%ss, Snapcast=%ss/%ss stale",
            self.monitor_coordinator.device_ping_interval,
            self.monitor_coordinator.device_ping_failure_threshold,
            self.monitor_coordinator.pulse_probe_interval,
            self.monitor_coordinator.snapcast_probe_interval,
            self.monitor_coordinator.snapcast_last_seen_timeout,
        )
        self._install_signal_handlers()
        self._start_pulse_listener()
        self._start_systemd_listener()
        self.reconcile(force=True)

        while not self.stop_event.is_set():
            now = time.monotonic()
            timeout = min(
                max(0.0, self.mpd_service.next_deadline - now),
                max(0.0, self.next_pulse_snapshot - now),
                max(0.0, self.snapserver_service.next_state_check - now),
                max(0.0, self.monitor_coordinator.next_check - now),
            )
            woke = self.pulse_wakeup.wait(timeout=timeout)
            self.pulse_wakeup.clear()
            self.reconcile(force=woke)

    def stop(self) -> None:
        """Stop listeners and release PulseAudio, MPD, and capture resources."""
        LOG.info("Stopping audio-manager")
        self.stop_event.set()
        self.pulse_wakeup.set()
        if self.systemd_loop is not None:
            self.systemd_loop.quit()
        self.pulse_router.close()
        self.mpd_service.disconnect()

    def _install_signal_handlers(self) -> None:
        """Convert service termination signals into a clean loop shutdown."""
        signal.signal(signal.SIGTERM, lambda _signum, _frame: self.stop_event.set())
        signal.signal(signal.SIGINT, lambda _signum, _frame: self.stop_event.set())

    def _start_pulse_listener(self) -> None:
        """Start the PulseAudio event listener owned by `PulseAudioRouter`."""
        self.pulse_router.start_event_listener(self.stop_event, self.pulse_wakeup)

    def _start_systemd_listener(self) -> None:
        """Start the systemd/Avahi discovery thread."""
        thread = threading.Thread(
            target=self.service_discovery.run,
            name="systemd-events",
            daemon=True,
        )
        thread.start()

    def _on_snapserver_state_changed(self, _active: bool) -> None:
        """Publish a Snapserver state transition to the shared runtime file."""
        self._write_active_clients()

    def reconcile(self, force: bool = False) -> None:
        """Synchronize services, audio routes, captures, and Snapcast streams.

        The order is intentional: remote health is updated first, then
        Snapserver presence, PulseAudio activity, capture processes, and finally
        the selected Snapcast stream.
        """
        now = time.monotonic()
        LOG.debug("Reconcile started: force=%s", force)

        # A topology change requests a debounced MPD restart. It is handled
        # before new monitoring results can schedule another restart.
        self.mpd_service.restart_if_due(now)

        # Read systemd state, then run only monitors whose deadlines expired.
        snapserver_active = self.snapserver_service.state(now)
        self.monitor_coordinator.reconcile(now, snapserver_active)

        # Avahi discovers clients; this policy decides whether Snapserver must
        # be running for the currently healthy remote Snapclients.
        with self.remote_clients_lock:
            known_clients = tuple(self.remote_snapclients)
        self.snapserver_service.reconcile_presence(
            known_clients,
            self.monitor_coordinator.device_availability,
            self.monitor_coordinator.snapcast_service_active,
            self.monitor_coordinator.snapcast_status_known,
        )
        if self.snapserver_service.consume_transition():
            LOG.info("Snapserver state: %s", "active" if snapserver_active else "inactive")
            if snapserver_active:
                # Null sinks and FIFOs are created only when Snapserver becomes
                # active; Bluetooth itself remains available without Snapcast.
                self.pulse_router.ensure_snapcast_paths()

        # PulseAudio snapshots are event-driven when `force` is true and are
        # also refreshed periodically as a safety net.
        if force or now >= self.next_pulse_snapshot or self.cached_pulse_snapshot is None:
            try:
                self.cached_pulse_snapshot = self.pulse_router.snapshot()
                self.next_pulse_snapshot = now + PULSE_SNAPSHOT_INTERVAL
                LOG.debug(
                    "PulseAudio snapshot: sinks=%d sources=%d sink_inputs=%d next=%.1fs",
                    len(self.cached_pulse_snapshot.sinks),
                    len(self.cached_pulse_snapshot.sources),
                    len(self.cached_pulse_snapshot.sink_inputs),
                    self.next_pulse_snapshot - now,
                )
            except Exception as exc:
                LOG.warning("PulseAudio state unavailable: %s", exc)
                return

        snapshot = self.cached_pulse_snapshot
        if snapshot is None:
            return
        activity = self.pulse_router.inspect_activity(snapshot)
        LOG.debug(
            "Audio activity: bluetooth_source=%s bluetooth_sink_active=%s "
            "pc_sink_active=%s mpd_active=%s snapserver_active=%s",
            activity.bluetooth_source,
            activity.bluetooth_sink_active,
            activity.pc_sink_active,
            self.mpd_service.output_active,
            snapserver_active,
        )

        # Route Bluetooth to Snapcast or directly to the physical sink, then
        # start/stop the Bluetooth and PC FIFO readers according to activity.
        self.pulse_router.reconcile_bluetooth(
            activity.bluetooth_source,
            snapserver_active,
            snapshot.sinks,
        )
        self.pulse_router.reconcile_captures(
            snapserver_active,
            activity.bluetooth_sink_active,
            activity.pc_sink_active,
            now,
        )

        if not snapserver_active:
            # No Snapserver means no MPD/Snapcast stream synchronization is
            # possible. Capture processes have already been stopped above.
            self.mpd_service.defer_output_check(now)
            return

        # MPD output state is deliberately checked less often than PulseAudio
        # events because it is read through a separate TCP protocol connection.
        self.mpd_service.refresh_if_due(now)

        desired_mode = self._desired_mode(
            activity.bluetooth_source,
            activity.pc_sink_active,
        )
        LOG.debug(
            "Source decision: desired=%s current=%s",
            desired_mode,
            self.snapserver_service.current_mode,
        )
        if desired_mode is not None:
            self.snapserver_service.sync_stream(desired_mode, now)

    def _desired_mode(self, bt_source: str | None, pc_active: bool) -> str | None:
        """Apply source priority: Bluetooth, PC, MPD, then MPD fallback."""
        if bt_source is not None:
            LOG.debug("Desired source: Bluetooth source is present")
            return "bluetooth"
        if pc_active:
            LOG.debug("Desired source: PC sink input is active")
            return "pc"
        if self.mpd_service.output_active:
            LOG.debug("Desired source: MPD snapcast output is enabled")
            return "mpd"
        if self.snapserver_service.current_mode == "bluetooth":
            LOG.debug("Desired source: Bluetooth ended, falling back from Bluetooth")
            return "pc" if pc_active else "mpd"
        LOG.debug("Desired source: MPD fallback")
        return "mpd"

def main() -> int:
    """Run the controller and always release resources during shutdown."""
    controller = Controller()
    try:
        controller.start()
    finally:
        controller.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
