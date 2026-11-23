#!/usr/bin/python3

"""Generate MPD outputs from audio-manager's active client state."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import re
import socket
import tempfile
import time

from mpd import CommandError, MPDClient


LOG = logging.getLogger("mpd-output-configurator")
logging.basicConfig(level=logging.INFO, format="[MPD-OUTPUTS] %(message)s")

CONFIG_PATH = Path("/etc/mpd.conf")
ACTIVE_CLIENTS_PATH = Path("/run/audio-manager/active-clients.json")
MPD_HOST = "127.0.0.1"
MPD_PORT = 6600
PLAYBACK_STATE_PATH = Path("/run/audio-manager/mpd-playback-state.json")
FALLBACK_OUTPUT_INDEX = 0
AUTO_START = "# BEGIN AUTO-GENERATED MPD OUTPUTS"
AUTO_END = "# END AUTO-GENERATED MPD OUTPUTS"
SNAPCAST_FIFO_OUTPUT = '''audio_output {
    type            "fifo"
    name            "snapcast"
    path            "/tmp/snapmpdfifo"
    format          "48000:16:2"
    enabled         "no"
}'''

AUDIO_OUTPUT_RE = re.compile(r"(?ms)^audio_output\s*\{.*?^\}\s*")
SERVER_RE = re.compile(r'^\s*server\s+"([^"]+)"\s*$', re.MULTILINE)


def _is_remote_pulse_output(block: str) -> bool:
    return (
        re.search(r'^\s*type\s+"pulse"\s*$', block, re.MULTILINE) is not None
        and SERVER_RE.search(block) is not None
    )


def _is_snapcast_fifo_output(block: str) -> bool:
    return (
        re.search(r'^\s*type\s+"fifo"\s*$', block, re.MULTILINE) is not None
        and re.search(r'^\s*name\s+"snapcast"\s*$', block, re.MULTILINE) is not None
    )


def _local_names() -> set[str]:
    names = {socket.gethostname().lower(), socket.getfqdn().lower()}
    names.update({f"{name}.local" for name in tuple(names)})
    return names


def _client_display_name(client: dict, hostname: str) -> str:
    """Return the human-readable name used for an MPD PulseAudio output."""

    explicit_name = client.get("display_name")
    if isinstance(explicit_name, str) and explicit_name.strip():
        return explicit_name.strip()

    short_hostname = hostname.split(".", 1)[0].strip()
    if short_hostname:
        return short_hostname
    return str(client.get("id", "remote-pulse"))


def _quote_mpd_string(value: str) -> str:
    """Escape a value before placing it inside an MPD quoted string."""

    return value.replace("\\", "\\\\").replace('"', '\\"')


def _connect_mpd() -> MPDClient | None:
    """Connect to MPD, retrying briefly while systemd finishes its start."""

    last_error: Exception | None = None
    for _ in range(20):
        client = MPDClient()
        client.timeout = 1
        try:
            client.connect(MPD_HOST, MPD_PORT)
            return client
        except Exception as error:  # pragma: no cover - depends on MPD/socket state
            last_error = error
            try:
                client.disconnect()
            except Exception:
                pass
            time.sleep(0.25)
    LOG.warning("Could not connect to MPD: %s", last_error)
    return None


def _disconnect_mpd(client: MPDClient) -> None:
    """Close an MPD connection without hiding the main operation result."""

    try:
        client.disconnect()
    except Exception:
        pass


def _write_playback_state(state: dict) -> None:
    """Atomically save the MPD state used across a service restart."""

    PLAYBACK_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=PLAYBACK_STATE_PATH.parent,
            prefix=f".{PLAYBACK_STATE_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(state, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, PLAYBACK_STATE_PATH)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise


def save_playback_state() -> int:
    """Save active outputs and playback position before MPD is stopped."""

    client = _connect_mpd()
    if client is None:
        return 0
    try:
        status = client.status()
        current_song = client.currentsong()
        outputs = client.outputs()
        state = {
            "state": str(status.get("state", "stop")),
            "song": {
                "id": status.get("songid") or current_song.get("id"),
                "file": current_song.get("file"),
                "position": current_song.get("pos"),
                "elapsed": status.get("elapsed"),
            },
            "enabled_outputs": sorted(
                str(output.get("outputname"))
                for output in outputs
                if output.get("outputname")
                and output.get("outputenabled") == "1"
            ),
        }
        _write_playback_state(state)
    except Exception as error:
        LOG.warning("Could not save MPD playback state: %s", error)
        return 0
    finally:
        _disconnect_mpd(client)

    LOG.info(
        "Saved MPD playback state: %s, active outputs: %s",
        state["state"],
        ", ".join(state["enabled_outputs"]) or "none",
    )
    return 0


def _restore_song_state(client: MPDClient, state: dict) -> None:
    """Restore the saved song, playback state, and elapsed position."""

    song = state.get("song", {})
    if not isinstance(song, dict):
        song = {}
    song_id = song.get("id")
    current_song = client.currentsong()
    if song_id and str(current_song.get("id")) != str(song_id):
        client.playid(str(song_id))

    playback_state = state.get("state", "stop")
    if playback_state == "play":
        client.play()
    elif playback_state == "pause":
        client.pause(1)
    else:
        client.stop()

    elapsed = song.get("elapsed")
    if elapsed is not None and playback_state in {"play", "pause"}:
        client.seekcur(str(elapsed))


def restore_playback_state() -> int:
    """Restore saved outputs and playback after MPD has started."""

    try:
        state = json.loads(PLAYBACK_STATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 0
    except (OSError, json.JSONDecodeError) as error:
        LOG.warning("Could not read saved MPD playback state: %s", error)
        try:
            PLAYBACK_STATE_PATH.unlink()
        except OSError:
            pass
        return 0

    client = _connect_mpd()
    if client is None:
        return 0

    restored_outputs: list[str] = []
    try:
        enabled_names = {
            str(name)
            for name in state.get("enabled_outputs", [])
            if isinstance(name, str)
        }
        outputs = client.outputs()
        for output in outputs:
            output_name = str(output.get("outputname", ""))
            output_id = str(output.get("outputid", ""))
            if not output_name or not output_id.isdigit():
                continue
            if output_name not in enabled_names:
                continue
            if output.get("outputenabled") != "1":
                client.enableoutput(output_id)
            restored_outputs.append(output_name)

        if not restored_outputs:
            fallback = (
                outputs[FALLBACK_OUTPUT_INDEX]
                if len(outputs) > FALLBACK_OUTPUT_INDEX
                else None
            )
            if fallback is not None and str(fallback.get("outputid", "")).isdigit():
                fallback_id = str(fallback["outputid"])
                fallback_name = str(fallback.get("outputname", fallback_id))
                if fallback.get("outputenabled") != "1":
                    client.enableoutput(fallback_id)
                restored_outputs.append(fallback_name)
                LOG.info(
                    "No saved MPD output is available; enabled fallback output at index %d: %s",
                    FALLBACK_OUTPUT_INDEX,
                    fallback_name,
                )

        if restored_outputs:
            _restore_song_state(client, state)
            LOG.info(
                "Restored MPD playback: %s; active outputs: %s",
                state.get("state", "stop"),
                ", ".join(restored_outputs),
            )
        else:
            LOG.info("No saved MPD output or fallback is available; playback remains stopped")
    except Exception as error:
        LOG.warning("Could not restore MPD playback state: %s", error)
    finally:
        _disconnect_mpd(client)
        try:
            PLAYBACK_STATE_PATH.unlink()
        except OSError:
            pass
    return 0


def enable_single_output() -> int:
    """Enable the only normal output when MPD restored no usable output.

    MPD restores output enabled/disabled state from ``state_file``.  If MPD
    has exactly one configured output, it must be enabled after startup so
    that playback has at least one possible destination.
    """

    last_error: Exception | None = None
    for _ in range(20):
        client = MPDClient()
        client.timeout = 1
        try:
            client.connect(MPD_HOST, MPD_PORT)
            outputs = client.outputs()
            break
        except (CommandError, OSError, TimeoutError) as error:
            last_error = error
            time.sleep(0.25)
        finally:
            try:
                client.disconnect()
            except (OSError, TimeoutError):
                pass
    else:
        LOG.warning("Could not query MPD outputs after startup: %s", last_error)
        return 0

    if len(outputs) != 1:
        LOG.info(
            "Keeping MPD output state; outputs available: %d",
            len(outputs),
        )
        return 0

    output = outputs[0]
    output_id = output.get("outputid")
    if not output_id or not output_id.isdigit():
        LOG.warning("The only MPD output has no valid output id: %s", output)
        return 0
    if output.get("outputenabled") == "1":
        LOG.info("The only MPD output is already enabled: %s", output.get("outputname"))
        return 0

    client = MPDClient()
    client.timeout = 1
    try:
        client.connect(MPD_HOST, MPD_PORT)
        client.enableoutput(output_id)
    except (CommandError, OSError, TimeoutError) as error:
        LOG.warning("Could not enable the only MPD output: %s", error)
        return 0
    finally:
        try:
            client.disconnect()
        except (OSError, TimeoutError):
            pass
    LOG.info("Enabled the only MPD output: %s", output.get("outputname"))
    return 0


def discover_active_clients() -> tuple[dict[str, tuple[str, str]], bool]:
    """Read current PulseAudio and Snapclient state from audio-manager."""

    for _ in range(20):
        if ACTIVE_CLIENTS_PATH.exists():
            break
        time.sleep(0.25)
    try:
        payload = json.loads(ACTIVE_CLIENTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Could not read active client state: %s", exc)
        return {}, False

    discovered: dict[str, tuple[str, str]] = {}
    snapclients = False
    local_names = _local_names()
    for client in payload.get("clients", []):
        if not isinstance(client, dict):
            continue
        hostname_raw = str(client.get("hostname", "")).rstrip(".")
        display_name = _client_display_name(client, hostname_raw)
        fqdn = hostname_raw if "." in hostname_raw else f"{hostname_raw}.local"
        if not hostname_raw or fqdn.lower() in local_names:
            continue

        pulse = client.get("pulse", {})
        if isinstance(pulse, dict) and pulse.get("active") is True:
            try:
                addresses = client.get("addresses", [])
                address = next(
                    (str(value) for value in addresses if "." in str(value)),
                    None,
                )
                if address is None:
                    address = socket.getaddrinfo(
                        fqdn,
                        int(pulse.get("port", 4713)),
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                    )[0][4][0]
                discovered[fqdn.lower()] = (address, display_name)
            except (OSError, socket.gaierror) as exc:
                LOG.warning("Could not resolve active PulseAudio client %s: %s", fqdn, exc)

        snapclient = client.get("snapclient", {})
        if isinstance(snapclient, dict) and snapclient.get("active") is True:
            snapclients = True

    return discovered, snapclients


def _generated_section(outputs: list[str]) -> str:
    lines = [
        AUTO_START,
        "# Generated by mpd-output-configurator.py; do not edit manually.",
    ]
    if outputs:
        lines.extend(output.rstrip() for output in outputs)
    else:
        lines.append("# No remote PulseAudio outputs are currently available.")
    lines.append(AUTO_END)
    return "\n".join(lines) + "\n"


def update_config(
    discovered: dict[str, tuple[str, str]], snapclients: bool
) -> bool:
    original = CONFIG_PATH.read_text(encoding="utf-8")

    base = re.sub(
        rf"\n?{re.escape(AUTO_START)}.*?{re.escape(AUTO_END)}\n?",
        "\n",
        original,
        flags=re.DOTALL,
    )
    base = AUDIO_OUTPUT_RE.sub(
        lambda match: ""
        if _is_remote_pulse_output(match.group(0))
        or _is_snapcast_fifo_output(match.group(0))
        else match.group(0),
        base,
    ).rstrip()

    generated: list[str] = []
    for fqdn, (address, display_name) in sorted(discovered.items()):
        escaped_name = _quote_mpd_string(display_name)
        block = (
            'audio_output {\n'
            '    type "pulse"\n'
            f'    server "{address}"\n'
            f'    name "{escaped_name}"\n'
            '}'
        )
        generated.append(block)

    if snapclients:
        generated.append(SNAPCAST_FIFO_OUTPUT)

    updated = f"{base}\n\n{_generated_section(generated)}"
    if updated == original:
        return False

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=CONFIG_PATH.parent, delete=False
    ) as temporary:
        temporary.write(updated)
        temporary_path = Path(temporary.name)
    os.chmod(temporary_path, CONFIG_PATH.stat().st_mode)
    os.replace(temporary_path, CONFIG_PATH)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--enable-single-output",
        action="store_true",
        help="enable the only normal output after MPD has started",
    )
    actions.add_argument(
        "--save-playback-state",
        action="store_true",
        help="save active outputs and playback before MPD is stopped",
    )
    actions.add_argument(
        "--restore-playback-state",
        action="store_true",
        help="restore outputs and playback after MPD has started",
    )
    args = parser.parse_args()
    if args.enable_single_output:
        return enable_single_output()
    if args.save_playback_state:
        return save_playback_state()
    if args.restore_playback_state:
        return restore_playback_state()

    try:
        discovered, snapclients = discover_active_clients()
    except OSError as exc:
        LOG.warning("Active client state unavailable; keeping existing MPD outputs: %s", exc)
        return 0

    changed = update_config(discovered, snapclients)
    LOG.info(
        "%s MPD configuration; discovered remote PulseAudio outputs: %d",
        "Updated" if changed else "Kept",
        len(discovered),
    )
    LOG.info("Discovered remote Snapclients: %d", 1 if snapclients else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
