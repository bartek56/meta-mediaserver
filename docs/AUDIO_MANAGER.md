# Audio Manager

`audio-manager` coordinates Bluetooth, PulseAudio, MPD, and Snapcast on the
MediaServer. It is installed as `audio-manager.service` and runs continuously,
including when `snapserver.service` is stopped.

The manager does not use the built-in Raspberry Pi Bluetooth controller for
audio routing. It operates on the Bluetooth adapter and PulseAudio sinks and
sources available on the target system, including an additional USB adapter.

## Responsibilities

The manager is responsible for:

- discovering remote PulseAudio servers and Snapclients with Avahi;
- maintaining `/run/audio-manager/active-clients.json`;
- starting and stopping `snapserver.service` according to remote Snapclient
  presence;
- routing Bluetooth and PC audio into Snapcast FIFO streams;
- detecting whether MPD's `snapcast` output is enabled;
- selecting the active Snapcast stream for all Snapcast groups;
- stopping idle Bluetooth and PC capture processes after 60 seconds;
- requesting MPD configuration regeneration when remote PulseAudio topology
  changes.

## Service lifecycle

The service is started by systemd. Before the Python process starts, the unit
executes:

```text
bluetoothctl discoverable on
```

This makes the MediaServer discoverable to Bluetooth clients. The manager then
starts its PulseAudio event listener, systemd listener, and Avahi discovery.

The manager itself remains running when Snapcast is disabled. The remote
Snapclient list controls `snapserver.service` independently:

```text
at least one remote Snapclient  -> snapserver.service active
no remote Snapclients            -> snapserver.service stopped
```

The local MediaServer Snapclient is excluded from this decision.

## Client discovery

Two Avahi service types are monitored:

```text
_snapclient._tcp
_pulse-server._tcp
```

The permanent Avahi browsers react immediately to `ItemNew` and `ItemRemove`.
Every five seconds the manager also creates a temporary Avahi browser and
reconciles the currently known services with the current Avahi result. This
handles devices that disappear without sending a clean Avahi goodbye packet.

The two service types are tracked independently. A device can therefore have
one active service and one inactive service, for example:

```json
{
  "pulse": { "active": false },
  "snapclient": { "active": true }
}
```

## Liveness checks

### PulseAudio

For a discovered PulseAudio service, the manager resolves its address and
checks TCP port `4713`. The check uses a short timeout and succeeds when at
least one known IPv4 address accepts the connection.

If the service is present in Avahi but port `4713` does not respond, the
manager requires three consecutive failed probes before expiring the
PulseAudio service. A successful probe resets the failure counter. This avoids
removing a client because of one temporary network or PulseAudio startup
failure. The manager then:

1. updates `active-clients.json`;
2. removes the corresponding remote MPD output on the next configuration run;
3. schedules an MPD restart after the topology-change debounce interval.

### Snapclient

Snapclient is not checked by opening TCP port `1704`; the client publishes the
Avahi service but does not provide a server endpoint suitable for this probe.

When Snapserver is available, the manager additionally queries its JSON-RPC
`Server.GetStatus` method. If a known client is reported with
`"connected": false`, it is removed even if a stale Avahi announcement still
exists. If the Snapserver API is unavailable, Avahi remains the source of
truth so that a newly discovered client can cause Snapserver startup.

The periodic reconciliation also adds services that are present again in the
current Avahi result. This allows a client that was powered off and then
started again to return without restarting `audio-manager.service`.

## Active-client state file

The manager atomically writes:

```text
/run/audio-manager/active-clients.json
```

The file contains the schema version, generation time, client identity,
resolved addresses, and independent PulseAudio/Snapclient status:

```json
{
  "schema": 1,
  "generated_at": "2026-10-25T13:12:35Z",
  "clients": [
    {
      "id": "MediaClientTV",
      "hostname": "MediaClientTV.local",
      "addresses": ["192.168.1.6"],
      "pulse": {
        "active": true,
        "port": 4713
      },
      "snapclient": {
        "active": true,
        "port": 1704
      }
    }
  ]
}
```

The file is runtime state and is not intended to be edited manually.

## MPD integration

`mpd-output-configurator.py` reads `active-clients.json` and updates the
auto-generated section at the end of `/etc/mpd.conf`.

Remote PulseAudio outputs are generated only for clients with
`pulse.active: true`. The Snapcast FIFO output is generated only when at least
one remote Snapclient is active:

```conf
audio_output {
    type            "fifo"
    name            "snapcast"
    path            "/tmp/snapmpdfifo"
    format          "48000:16:2"
    enabled         "no"
}
```

The FIFO is deliberately disabled by default. The user or an application can
enable it through the MPD protocol, for example:

```bash
mpc enable snapcast
```

The generated section is delimited by:

```text
# BEGIN AUTO-GENERATED MPD OUTPUTS
# END AUTO-GENERATED MPD OUTPUTS
```

User configuration outside this section is preserved. MPD is restarted after a
remote PulseAudio service is added or removed, allowing the list of outputs to
match the currently available clients.

## Audio capture and streams

Bluetooth and PC audio are captured continuously only while needed. The
manager uses these PulseAudio sinks and FIFOs:

| Input | PulseAudio sink | FIFO | Snapcast stream |
|---|---|---|---|
| Bluetooth | `snapcast_bt` | `/tmp/snapbtfifo` | `Bluetooth` |
| PC PulseAudio | `snapcast_pc` | `/tmp/snappcfifo` | `PC` |
| MPD | MPD FIFO output | `/tmp/snapmpdfifo` | `MPD` |

If Bluetooth or PC capture has no audio activity for 60 seconds, its capture
process is stopped. It is started again when activity is detected.

## Source selection

The desired source is evaluated from the current inputs:

1. Bluetooth, when a Bluetooth source is active;
2. PC, when a PC Snapcast input is active and Bluetooth is not active;
3. MPD, when the MPD `snapcast` output is enabled;
4. MPD as the fallback mode when no higher-priority source is active.

Every five seconds, and after relevant events, the manager queries Snapcast
groups. Any group whose current stream differs from the desired stream receives
`Group.SetStream`. This also corrects groups changed manually in the Snapcast
application.

When Bluetooth disconnects, the manager does not blindly choose PC. It first
checks whether PC is active; otherwise it falls back to MPD. When Bluetooth
and PC are both inactive, MPD remains the default source if its Snapcast
output is enabled.

## Useful diagnostics

Check the services:

```bash
systemctl status audio-manager.service
systemctl status snapserver.service
systemctl status mpd.service
```

Inspect the current client state:

```bash
cat /run/audio-manager/active-clients.json
```

Inspect MPD outputs:

```bash
mpc outputs
```

Inspect Avahi announcements:

```bash
avahi-browse -rt _pulse-server._tcp
avahi-browse -rt _snapclient._tcp
```

Inspect the Snapserver status:

```bash
curl -sS http://127.0.0.1:1780/jsonrpc \
  -H 'Content-Type: application/json' \
  --data '{"id":1,"jsonrpc":"2.0","method":"Server.GetStatus"}'
```

Follow manager decisions:

```bash
journalctl -u audio-manager.service -f
```

Important log messages include:

- `Remote ... discovered` — Avahi found a service;
- `Remote ... removed` — Avahi sent an explicit removal;
- `... expired from Avahi poll` — periodic reconciliation removed a stale
  service;
- `Restarting MPD: remote PulseAudio topology changed` — MPD output topology
  changed;
- `Active source mode: ...` — Snapcast groups were switched to a source.

