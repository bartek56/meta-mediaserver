# Audio Manager

`audio-manager` is the event-driven Python service that connects the local
Bluetooth/PulseAudio setup with Snapcast and monitors remote MediaServer
clients. The current implementation is packaged as `audio-manager` and runs
as `audio-manager.service`.

The application remains running even when there are no remote Snapclients and
when `snapserver.service` is stopped. In that state it continues to receive
Avahi and systemd events, monitor known devices, and check local PulseAudio
state. Snapcast-specific polling and capture processes are disabled.

## Responsibilities

The application is responsible for:

- discovering remote `_snapclient._tcp` and `_pulse-server._tcp` services with
  Avahi;
- maintaining one state record per remote device;
- checking host reachability, remote PulseAudio availability, and Snapclient
  status;
- writing `/run/audio-manager/active-clients.json` atomically;
- starting or stopping `snapserver.service` according to remote Snapclient
  presence;
- creating the local PulseAudio sinks and FIFOs used by Snapserver;
- routing Bluetooth audio to Snapcast or to the physical sink;
- keeping the Bluetooth loopback volume at `120%`;
- starting `parec` capture processes only when the corresponding sink is in
  use;
- requesting an MPD restart only after a new active remote PulseAudio or
  Snapclient service appears, a known service is removed, or a known host
  reaches the unavailable ping threshold;
- selecting the `Bluetooth`, `PC`, or `MPD` stream for every Snapcast group.

The application does not replace Snapserver. Stream definitions remain
configured in `/etc/snapserver.conf`; the manager uses Snapcast JSON-RPC
`Group.SetStream` to select the active input for every group.

## Source layout

The installed entry point is a thin launcher:

```text
/usr/bin/audio-manager.py
```

The Python package is installed below `audio_manager/`:

| Module | Responsibility |
|---|---|
| `app.py` | Composition root, runtime configuration, startup and shutdown. |
| `scheduler.py` | Main event loop, monotonic timers, and worker pool. |
| `events.py` | Event and worker-result data structures. |
| `avahi.py` | Avahi D-Bus browsers and service resolution. |
| `monitoring.py` | Per-device ping/PulseAudio monitoring and the shared Snapcast poller. |
| `lifecycle.py` | Snapserver desired-state policy and systemd reconciliation. |
| `audio.py` | PulseAudio sinks, Bluetooth loopback, FIFOs, captures, MPD restart coordination, and Snapcast stream selection. |
| `adapters.py` | Blocking system integrations: ping, `pactl`, JSON-RPC, and systemd D-Bus. |
| `models.py` | Device and service state models. |
| `registry.py` | In-memory device registry. |
| `persistence.py` | Atomic publication of the active-client state file. |

Source files are located in:

```text
recipes-multimedia/snapcast-bt/snapcast-bt/audio_manager/
```

## Main event loop

The main loop is `EventLoop` in `scheduler.py`. It is deliberately not a
busy-wait loop:

1. queued callbacks are drained;
2. timers whose deadlines have elapsed are executed;
3. the loop waits on a condition variable until either a new event arrives or
   the next timer is due.

The scheduler uses `time.monotonic()`. Periodic timers use fixed deadlines and
skip missed periods instead of creating a burst of catch-up calls.

Blocking operations never run in the event-loop thread. `WorkerPool` runs
ping, remote PulseAudio handshakes, Snapcast JSON-RPC calls, and systemd
commands in worker threads. Completion callbacks are posted back to the main
loop.

### Where events enter the queue

The queue contains callbacks (`Callable[[], None]`), not raw event objects.
Events are converted to callbacks at these boundaries:

| Producer | Queue operation | Main-loop action |
|---|---|---|
| Avahi D-Bus thread | `AudioManagerApplication._post_event()` → `loop.post()` | Register, resolve, or remove a service. |
| systemd D-Bus listener | `_on_systemd_state()` → `_post_event()` | Update Snapserver state and reconcile desired state. |
| Worker pool | completion callback → `loop.post()` | Apply ping, PulseAudio, JSON-RPC, or systemd results. |
| Monotonic scheduler | timer callback executed by `run_due()` | Start a periodic probe or reconcile operation. |

The typed events in `events.py` include `ServiceDiscovered`,
`ServiceResolved`, `ServiceRemoved`, `PulseAudioEvent`, `SystemdStateChanged`, `PingCompleted`,
`PulseProbeCompleted`, and `SnapcastStatusCompleted`.

## Startup and shutdown

`AudioManagerApplication.run()` performs the following steps:

1. installs `SIGTERM` and `SIGINT` handlers;
2. publishes an initial empty client state;
3. starts the Snapserver supervisor and its 30-second systemd fallback timer;
4. performs the initial local audio reconciliation and starts `pactl subscribe`;
5. starts Avahi discovery in its GLib thread;
6. starts the systemd D-Bus listener;
7. enters the event loop.

On shutdown, listeners and timers are stopped, device monitors are cancelled,
capture processes are terminated, PulseAudio is closed, and worker threads
are joined.

The systemd unit also runs:

```text
bluetoothctl discoverable on
```

before starting the Python process. It sets the PulseAudio runtime paths for
the root PulseAudio instance and enables debug logging by default:

```text
XDG_RUNTIME_DIR=/run/user/0
PULSE_RUNTIME_PATH=/run/user/0/pulse
AUDIO_MANAGER_LOG_LEVEL=DEBUG
```

## Device discovery and state

Avahi creates two permanent D-Bus service browsers:

```text
_snapclient._tcp
_pulse-server._tcp
```

The application handles `ItemNew`, `ItemRemove`, and the resolver's `Found`
signal. Services belonging to the local host are ignored. A resolved service
is represented by a `ServiceKey` containing its type, interface, protocol, and
instance name.

Snapclient and PulseAudio advertisements are independent. Names are normalized
so, for example, `Snapclient-Office` and `pulse@Office` refer to the same
device record (`office`). Removing one service does not remove the other.

Each device has separate state for:

- host reachability;
- PulseAudio availability;
- Snapclient availability;
- consecutive failure counters;
- resolved addresses and last Snapcast observation.

### Active-client state file

The registry is published atomically to:

```text
/run/audio-manager/active-clients.json
```

Only devices whose host status is `available` are included. PulseAudio and
Snapclient status inside an included device remains independent.

Example:

```json
{
  "clients": [
    {
      "addresses": ["192.168.1.7"],
      "display_name": "Office",
      "hostname": "Office.local",
      "host": {"active": true},
      "id": "office",
      "pulse": {"active": true, "port": 4713},
      "snapclient": {"active": true, "port": 1704}
    }
  ],
  "generated_at": "2026-10-26T10:00:00+00:00",
  "schema": 1
}
```

The timestamp is updated on every attempted publication, but the file is only
replaced when the state content changes.

## Monitoring and timers

The default values are defined by `AudioManagerConfig` in `app.py`:

| Operation | Default | Behaviour |
|---|---:|---|
| Host ping | 5 s per device | One IPv4 `ping` is submitted at a time. Three consecutive failures make the host unavailable. |
| Recovery ping | 30 s per unavailable device | Runs only while Avahi still retains at least one service for an unavailable device. It stops when Avahi removes the last service. |
| Remote PulseAudio handshake | 5 s per device | Runs `pactl -s tcp:<address>:<port> info`; timeout is 1 s. |
| Snapcast status poll | 2 s globally | One `Server.GetStatus` request covers all known devices. It runs only while Snapserver is active. |
| Snapclient invalid-status threshold | 2 polls | After two invalid observations, `snapclient.active` becomes false. |
| Accepted `lastSeen` age | 5 s | A client must be connected and have a recent `lastSeen` value. |
| Local PulseAudio reconciliation | PulseAudio events | `pactl subscribe` wakes the application for relevant source, source-output, module, and sink-input changes. Sink-only mute events are ignored. It also runs immediately at startup and on Snapserver transitions. |
| systemd fallback read | 30 s | Re-reads `snapserver.service` if a D-Bus state signal was missed. The first read is immediate. |
| MPD restart debounce | 3 s | Coalesces several device-state changes into one restart request. |
| Idle capture timeout | 60 s | Stops an inactive Bluetooth or PC `parec` process. |

There is no periodic local PulseAudio query and no per-device
`Server.GetStatus` request. The status poller is shared by all devices and
guards against overlapping requests.

### Failure semantics

The two failure mechanisms have different purposes:

- three failed pings change the host state to `unavailable`; the device is
  then excluded from the active-client file and no longer keeps Snapserver
  desired;
- after that transition, only a 30-second recovery ping remains while Avahi
  retains the service record; the ping monitor is stopped when Avahi removes
  the last service;
- two invalid `Server.GetStatus` observations change only the Snapclient
  service state to inactive. The Avahi service and host record remain present.

When Snapserver stops, the shared status poller is disabled immediately and
Snapclient states are reset to `unknown`. When it starts again, polling begins
immediately and resumes every two seconds.

## Snapserver lifecycle

`SnapserverDesiredStatePolicy` requests Snapserver when at least one device:

1. advertises `_snapclient._tcp`; and
2. has host status `available` after ping monitoring.

The policy intentionally does not require a successful `Server.GetStatus`
response to start Snapserver. Otherwise a stopped Snapserver could not be
started just because a new client was discovered.

The lifecycle is:

```text
Avahi discovers remote Snapclient
        |
        v
Ping succeeds -> desired state: running -> systemd StartUnit
        |
        v
Snapserver ActiveState=active -> enable shared Server.GetStatus poller
        |
        v
No available remote Snapclients -> desired state: stopped -> systemd StopUnit
        |
        v
Snapserver ActiveState=inactive -> disable poller and stop captures
```

The D-Bus `PropertiesChanged` signal is authoritative. The 30-second systemd
fallback repairs the state if that signal is lost.

When Snapserver is inactive, the application still:

- remains in the main event loop;
- receives Avahi and systemd events;
- receives local PulseAudio events from `pactl subscribe`;
- runs ping and remote PulseAudio checks for known devices;
- publishes the active-client state;
- reconciles local Bluetooth routing after PulseAudio events;
- keeps capture processes stopped.

## Local PulseAudio and Snapcast audio path

When Snapserver is active, `SnapcastAudioPipeline` ensures:

| Purpose | PulseAudio/FIFO name |
|---|---|
| Bluetooth null sink | `snapcast_bt` |
| PC null sink | `snapcast_pc` |
| Bluetooth capture FIFO | `/tmp/snapbtfifo` |
| PC capture FIFO | `/tmp/snappcfifo` |

The supplied Snapserver configuration consumes these paths as streams named
`Bluetooth` and `PC`. MPD supplies the `MPD` stream through
`/tmp/snapmpdfifo`.

`CaptureManager` checks whether a null sink has an uncorked sink input. If it
does, it starts:

```text
parec -d <sink>.monitor --format=s16le --rate=48000 --channels=2
```

The process writes to the corresponding FIFO. If there is no active sink input
for 60 seconds, the process is stopped. This is why a running
`audio-manager.service` does not imply that `parec` is continuously consuming
CPU.

## Bluetooth routing

`BluetoothRouter` searches for the first source whose name starts with one of:

```text
bluez_source
bluez_input
alsa_input.usb
```

When Snapserver is active, the loopback target is `snapcast_bt`. When
Snapserver is inactive, the target is selected in this order:

1. `alsa_output.headphones.stereo-fallback`;
2. the current default sink, if it is not a Snapcast sink;
3. the first `alsa_output.*` sink.

The loopback is created as:

```text
module-loopback source=<source> sink=<target> latency_msec=10
```

Its sink-input volume is explicitly set to a linear gain of `1.2`, which is
`120%` (`+4.75 dB`). The value is applied after a new loopback module is
created. Stable reconciliations do not write the volume again.

If no Bluetooth source or target sink exists, loopbacks belonging to the
previous Bluetooth source are unloaded.

When the Bluetooth route becomes active, the manager requests
`Group.SetStream(stream_id="Bluetooth")` for every Snapcast group. When
Bluetooth is disconnected, the stream selected before Bluetooth is restored:
`MPD` or `PC`. If no previous stream is available, the manager selects `PC`
when its sink has an active input, otherwise `MPD`. These requests are
asynchronous and do not restart MPD.

## MPD integration

`MpdCoordinator` compares the previous and current active remote PulseAudio
and Snapclient sets. When either set changes, it schedules an `mpd.service`
restart after the three-second debounce interval. A host timeout clears the
device's active service state, so the device is removed from the next MPD
configuration generated from `active-clients.json`. Local Bluetooth routing
and Snapcast stream selection never call `mpd.service`.

The MPD service's `ExecStartPre` runs `mpd-output-configurator.py`. That helper
reads `active-clients.json` and regenerates the marked section of
`/etc/mpd.conf`:

```text
# BEGIN AUTO-GENERATED MPD OUTPUTS
# END AUTO-GENERATED MPD OUTPUTS
```

The generated section contains active remote PulseAudio outputs and the
Snapcast FIFO output when at least one Snapclient is active. Configuration
outside that section is preserved.

The `name` of a generated remote PulseAudio output comes from the device's
`display_name`. This is the human-readable part of the Avahi service name,
for example `MediaClientOffice` from `pulse@MediaClientOffice`. The lowercase
`id` (for example `mediaclientoffice`) remains the stable internal identifier
and is not used as the user-facing MPD output name. Remote PulseAudio output
blocks are generated from the current state during the MPD service startup.

## Runtime configuration

All values can be overridden with environment variables. Invalid or nonpositive
numeric values are ignored and the documented default is used.

| Variable | Default |
|---|---:|
| `AUDIO_MANAGER_ACTIVE_CLIENTS_PATH` | `/run/audio-manager/active-clients.json` |
| `AUDIO_MANAGER_PING_INTERVAL` | `5` |
| `AUDIO_MANAGER_RECOVERY_PING_INTERVAL` | `30` |
| `AUDIO_MANAGER_PING_FAILURE_THRESHOLD` | `3` |
| `AUDIO_MANAGER_PULSE_INTERVAL` | `5` |
| `AUDIO_MANAGER_PULSE_TIMEOUT` | `1` |
| `AUDIO_MANAGER_SNAPCLIENT_INTERVAL` | `2` |
| `AUDIO_MANAGER_SNAPCLIENT_FAILURE_THRESHOLD` | `2` |
| `AUDIO_MANAGER_SNAPCLIENT_LAST_SEEN_MAX_AGE` | `5` |
| `AUDIO_MANAGER_SYSTEMD_FALLBACK_INTERVAL` | `30` |
| `AUDIO_MANAGER_CAPTURE_IDLE_TIMEOUT` | `60` |
| `AUDIO_MANAGER_MPD_RESTART_DEBOUNCE` | `3` |
| `AUDIO_MANAGER_LOG_LEVEL` | `INFO` |

The production service sets `AUDIO_MANAGER_LOG_LEVEL=DEBUG`.

## Logging

The application uses Python's `logging` package. It writes to standard error;
systemd captures the output in the journal. It does not create a separate log
file by default.

Follow all manager logs with:

```bash
journalctl -u audio-manager.service -f
```

Useful filters:

```bash
journalctl -u audio-manager.service --no-pager -o short-iso
journalctl -u audio-manager.service --no-pager | grep -E 'ERROR|WARNING|Bluetooth|Snapserver|loopback'
```

The logger names identify the component:

```text
audio-manager
audio-manager.adapters
audio-manager.audio
audio-manager.avahi
audio-manager.lifecycle
audio-manager.monitoring
audio-manager.persistence
audio-manager.scheduler
```

Typical messages include:

- `Avahi discovered ...` — a remote service appeared;
- `Ping succeeded ...` / `Device ... is unavailable ...` — host state changed;
- `Received Snapcast status for ... client(s)` — the shared RPC poll completed;
- `Snapclient ... removed from active state after 2 invalid status polls` — the
  Snapclient status threshold was reached;
- `Set ... loopback sink input(s) ... to 120%` — Bluetooth gain was applied;
- `PulseAudio event subscription started` / `PulseAudio event received ...` —
  the event-driven local audio path is active;
- `Starting snapserver.service ...` or `Stopping snapserver.service ...` —
  lifecycle policy requested a transition.

## Diagnostics

Check service state:

```bash
systemctl status audio-manager.service
systemctl show audio-manager.service \
  -p ActiveState -p SubState -p MainPID -p ExecMainStatus -p NRestarts
systemctl status snapserver.service
```

Inspect the published device state:

```bash
cat /run/audio-manager/active-clients.json
```

Inspect local PulseAudio objects:

```bash
export PULSE_RUNTIME_PATH=/run/user/0/pulse
pactl list sinks short
pactl list sources short
pactl list sink-inputs short
pactl list modules short | grep -E 'module-loopback|null-sink'
```

Inspect the Bluetooth loopback volume:

```bash
export PULSE_RUNTIME_PATH=/run/user/0/pulse
pactl list sink-inputs | sed -n '/Driver: module-loopback.c/,+12p'
```

The expected value is:

```text
Volume: front-left: ... / 120% / 4.75 dB,
        front-right: ... / 120% / 4.75 dB
```

Inspect Snapserver's current view:

```bash
curl -sS http://127.0.0.1:1780/jsonrpc \
  -H 'Content-Type: application/json' \
  --data '{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}'
```

Inspect Avahi advertisements:

```bash
avahi-browse -rt _snapclient._tcp
avahi-browse -rt _pulse-server._tcp
```

## Build and test

Run unit tests on the development machine:

```bash
PYTHONPATH=recipes-multimedia/snapcast-bt/snapcast-bt \
  pytest -q recipes-multimedia/snapcast-bt/tests/test_audio_manager.py
python3 -m compileall -q recipes-multimedia/snapcast-bt/snapcast-bt
git diff --check
```

Build on the supported builder (`msi_local`):

```bash
ssh msi_local \
  'cd /home/bartosz/workspace/yocto_mediaserver && \
   docker compose run --rm yocto bitbake audio-manager'
```

The resulting package is normally located at:

```text
build/tmp/deploy/ipk/cortexa72/audio-manager_1.0-r0_cortexa72.ipk
```

Install a built package on the target with:

```bash
scp audio-manager_1.0-r0_cortexa72.ipk mediaserver_local:/tmp/
ssh mediaserver_local \
  'opkg install --force-reinstall /tmp/audio-manager_1.0-r0_cortexa72.ipk'
```

After installation, verify the service, logs, active-client state, and
PulseAudio loopback volume using the commands above.

## Related files

- Recipe: `recipes-multimedia/snapcast-bt/audio-manager.bb`
- systemd unit: `recipes-multimedia/snapcast-bt/snapcast-bt/audio-manager.service`
- launcher: `recipes-multimedia/snapcast-bt/snapcast-bt/audio-manager.py`
- Snapserver streams: `recipes-multimedia/snapcast/snapcast/snapserver.conf`
- MPD state consumer: `recipes-multimedia/mpd/mpd/mpd-output-configurator.py`
- Unit tests: `recipes-multimedia/snapcast-bt/tests/test_audio_manager.py`
