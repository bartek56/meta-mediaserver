#!/usr/bin/env python3
"""System configuration domain for the MediaServer Textual application.

This module deliberately keeps system changes out of the UI.  It is also
usable from tests or another front end because it only depends on Python's
standard library.
"""

from __future__ import annotations

import json
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence


LOG = Callable[[str], None]
HOSTNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


@dataclass(frozen=True)
class ModeProfile:
    key: str
    label: str
    description: str
    legacy_script: str
    gui: bool
    jellyfin: bool
    webserver: bool
    snapserver: bool
    snapclient: bool


PROFILES: Mapping[str, ModeProfile] = {
    "MediaServer": ModeProfile(
        key="MediaServer",
        label="MediaServer",
        description="GUI, Jellyfin, web services, and Snapcast server",
        legacy_script="/opt/installScript.sh (Qt5 variant)",
        gui=True,
        jellyfin=True,
        webserver=True,
        snapserver=True,
        snapclient=False,
    ),
    "MediaClient": ModeProfile(
        key="MediaClient",
        label="MediaClient",
        description="Audio client mode with Snapcast client",
        legacy_script="/opt/installScript.sh (Base variant)",
        gui=False,
        jellyfin=False,
        webserver=False,
        snapserver=False,
        snapclient=True,
    ),
}


class CommandError(RuntimeError):
    """A command failed while changing the system."""


class CommandRunner:
    """Small, argument-list-only wrapper around subprocess."""

    def run(self, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                list(args),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            raise CommandError(f"{args[0]}: {exc}") from exc
        if check and result.returncode != 0:
            output = (result.stdout or "").strip()
            suffix = f": {output}" if output else ""
            raise CommandError(f"exit code {result.returncode}{suffix}")
        return result


def validate_hostname(hostname: str) -> str:
    """Validate a single RFC-compatible hostname label."""

    value = hostname.strip()
    if not value or len(value) > 63 or not HOSTNAME_RE.fullmatch(value):
        raise ValueError(
            "Hostname may contain only letters, digits, and hyphens "
            "(1–63 characters; it cannot start or end with a hyphen)."
        )
    return value


class SystemConfigurator:
    """Apply a selected profile and report every operation without set -e."""

    STATE_FILE = Path("/etc/mediaserver/system-configurator.json")
    NETWORK_CONFIG = Path("/etc/systemd/network/10-wired.network")
    DHCPCD_CONFIG = Path("/etc/dhcpcd.conf")
    NETWORK_INTERFACE = "eth0"
    NETWORK_BLOCK_BEGIN = "# BEGIN system-configurator static IPv4"
    NETWORK_BLOCK_END = "# END system-configurator static IPv4"
    WEB_SERVICES = ("apache2.service", "youtubedl-web.service", "filebrowser.service")
    COMMON_DISABLED = ("serial-getty@ttyS0.service", "getty@tty1.service", "dhcpcd.service")
    SERVICE_CATALOG = (
        ("mpd.service", "MPD"),
        ("snapserver.service", "Snapcast server"),
        ("snapclient.service", "Snapcast client"),
        ("tvheadend.service", "TVHeadend"),
        ("minidlnad.service", "MiniDLNA"),
        ("smb.service", "Samba"),
        ("nmb.service", "Samba NetBIOS"),
        ("vsftpd.service", "FTP server"),
        ("filebrowser.service", "File Browser"),
        ("transmission-daemon.service", "Transmission"),
        ("apache2.service", "Apache"),
        ("youtubedl-web.service", "YouTube DL Web"),
    )
    BOOTSTRAP_URL = (
        "https://github.com/twbs/bootstrap/releases/download/"
        "v5.0.0-beta1/bootstrap-5.0.0-beta1-dist.zip"
    )
    CLOCKPICKER_URL = "https://github.com/weareoutman/clockpicker/archive/gh-pages.zip"

    def __init__(self, runner: Optional[CommandRunner] = None, variant: str = "qt5") -> None:
        self.runner = runner or CommandRunner()
        self.variant = variant if variant in {"minimal", "base", "qt5"} else "qt5"

    def current_hostname(self) -> str:
        try:
            return socket.gethostname()
        except OSError:
            return "MediaServer"

    def system_mode(self) -> str:
        """Return the immutable mode determined by the image variant."""

        return "MediaClient" if self.variant == "minimal" else "MediaServer"

    def load_state(self) -> Dict[str, object]:
        try:
            with self.STATE_FILE.open(encoding="utf-8") as state_file:
                state = json.load(state_file)
            return state if isinstance(state, dict) else {}
        except (OSError, ValueError):
            return {}

    def load_network_config(self) -> Dict[str, object]:
        """Read the current Ethernet settings from systemd-networkd."""

        options: Dict[str, object] = {
            "static_ip": False,
            "interface": self.NETWORK_INTERFACE,
            "ip_address": "",
            "prefix_length": "24",
            "gateway": "",
            "dns": "",
        }
        try:
            lines = self.NETWORK_CONFIG.read_text(encoding="utf-8").splitlines()
        except OSError:
            return options

        address = ""
        dns_servers: List[str] = []
        dhcp_enabled = False
        for line in lines:
            key, separator, value = line.partition("=")
            if not separator:
                continue
            key = key.strip()
            value = value.strip()
            if key == "DHCP":
                dhcp_enabled = value.lower() not in {"", "no", "false", "0"}
            elif key == "Address" and not address:
                address = value
            elif key == "Gateway" and not options["gateway"]:
                options["gateway"] = value
            elif key == "DNS":
                dns_servers.append(value)

        if "/" in address and not dhcp_enabled:
            ip_address, prefix_length = address.split("/", 1)
            try:
                options["ip_address"] = str(ipaddress.IPv4Address(ip_address))
                options["prefix_length"] = str(int(prefix_length))
                options["static_ip"] = True
            except (ipaddress.AddressValueError, ValueError):
                pass
        options["dns"] = " ".join(dns_servers)
        return options

    def service_status(self, service: str) -> str:
        try:
            enabled = self.runner.run(["systemctl", "is-enabled", service], check=False)
            active = self.runner.run(["systemctl", "is-active", service], check=False)
        except CommandError as exc:
            return f"error: {exc}"
        enabled_text = (enabled.stdout or "unknown").strip()
        active_text = (active.stdout or "unknown").strip()
        return f"{active_text}, {enabled_text}"

    def service_exists(self, service: str) -> bool:
        try:
            result = self.runner.run(["systemctl", "is-enabled", service], check=False)
        except CommandError:
            return False
        return (result.stdout or "").strip() not in {"", "not-found"}

    def available_services(self) -> List[tuple[str, str, str]]:
        catalog = self.SERVICE_CATALOG
        if self.variant == "minimal":
            catalog = (("snapclient.service", "Snapcast client"),)
        result: List[tuple[str, str, str]] = []
        for service, label in catalog:
            if self.service_exists(service):
                key = re.sub(r"[^a-zA-Z0-9]+", "_", service).strip("_")
                result.append((key, label, service))
        return result

    def set_service_enabled(self, service: str, enabled: bool) -> None:
        self.runner.run(["systemctl", "enable" if enabled else "disable", service])

    def start_service(self, service: str) -> None:
        self.runner.run(["systemctl", "start", service])

    def stop_service(self, service: str) -> None:
        self.runner.run(["systemctl", "stop", service])

    def startup_step_completed(self, step: str, desired: bool = True) -> bool:
        """Return whether a startup configuration step matches the system."""

        def service_matches(service: str, enabled: bool) -> bool:
            try:
                active = self.runner.run(["systemctl", "is-active", service], check=False)
                state = self.runner.run(["systemctl", "is-enabled", service], check=False)
            except CommandError:
                return False
            active_ok = (active.stdout or "").strip() == ("active" if enabled else "inactive")
            enabled_ok = (state.stdout or "").strip() in (
                ("enabled", "static") if enabled else ("disabled", "masked", "indirect")
            )
            return active_ok and enabled_ok

        if step == "snapclient":
            return service_matches("snapclient.service", desired)
        if step == "snapserver":
            return service_matches("snapserver.service", desired)
        if step == "webserver":
            return all(service_matches(service, desired) for service in self.WEB_SERVICES)
        if step == "gui":
            service = "start.service" if desired else "startup.service"
            return service_matches(service, True)
        if step == "vim":
            return (Path("/home/root/.vim/bundle/Vundle.vim").exists()) == desired
        if step == "jellyfin":
            docker = shutil.which("docker") or "docker"
            try:
                result = self.runner.run(
                    [docker, "inspect", "-f", "{{.State.Running}}", "jellyfin"],
                    check=False,
                )
            except CommandError:
                return not desired
            running = result.returncode == 0 and (result.stdout or "").strip().lower() == "true"
            return running == desired
        return False

    def apply(
        self,
        mode: str,
        hostname: str,
        options: Optional[Mapping[str, object]] = None,
        log: Optional[LOG] = None,
    ) -> List[str]:
        mode = self.system_mode()
        profile = PROFILES[mode]
        hostname = validate_hostname(hostname)
        selected: Dict[str, object] = {
            "gui": profile.gui,
            "jellyfin": profile.jellyfin,
            "webserver": profile.webserver,
            "snapserver": profile.snapserver,
            "snapclient": profile.snapclient,
            "vim": True,
            "static_ip": False,
            "interface": self.NETWORK_INTERFACE,
            "ip_address": "",
            "prefix_length": "24",
            "gateway": "",
            "dns": "",
        }
        selected.update(options or {})
        selected.update(self._validate_network_options(selected))
        if self.variant == "minimal":
            selected.update(
                {
                    "gui": False,
                    "jellyfin": False,
                    "webserver": False,
                    "snapserver": False,
                    "snapclient": True,
                }
            )
        elif self.variant == "base":
            selected["gui"] = False
        messages: List[str] = []

        def emit(message: str) -> None:
            messages.append(message)
            if log:
                log(message)

        self._set_hostname(hostname, emit)
        self._configure_network(selected, emit)
        self._save_state(mode, hostname, selected, emit)
        emit("Configuration complete. The system will not restart automatically.")
        return messages

    def reboot(self) -> None:
        self.runner.run(["systemctl", "reboot"])

    def _try(self, description: str, action: Callable[[], None], log: LOG) -> None:
        try:
            action()
            log(f"OK: {description}")
        except (CommandError, OSError, ValueError, urllib.error.URLError, zipfile.BadZipFile) as exc:
            log(f"WARNING: {description}: {exc}")

    def _set_hostname(self, hostname: str, log: LOG) -> None:
        self._try(
            f"setting hostname to {hostname}",
            lambda: self.runner.run(["hostnamectl", "set-hostname", hostname]),
            log,
        )

    @staticmethod
    def _validate_ipv4(value: str, label: str, required: bool = False) -> str:
        value = value.strip()
        if not value and not required:
            return ""
        try:
            return str(ipaddress.IPv4Address(value))
        except ipaddress.AddressValueError as exc:
            requirement = " is required" if required else " must be a valid IPv4 address"
            raise ValueError(f"{label}{requirement}") from exc

    def _validate_network_options(self, options: Mapping[str, object]) -> Dict[str, object]:
        static_ip = bool(options.get("static_ip", False))
        result: Dict[str, object] = {
            "static_ip": static_ip,
            "interface": self.NETWORK_INTERFACE,
            "ip_address": str(options.get("ip_address", "")).strip(),
            "prefix_length": str(options.get("prefix_length", "24")).strip(),
            "gateway": str(options.get("gateway", "")).strip(),
            "dns": str(options.get("dns", "")).strip(),
        }
        if not static_ip:
            return result

        result["ip_address"] = self._validate_ipv4(str(result["ip_address"]), "IP address", True)
        try:
            prefix = int(str(result["prefix_length"]))
        except ValueError as exc:
            raise ValueError("Prefix length must be a number between 0 and 32") from exc
        if not 0 <= prefix <= 32:
            raise ValueError("Prefix length must be a number between 0 and 32")
        result["prefix_length"] = str(prefix)
        result["gateway"] = self._validate_ipv4(str(result["gateway"]), "Gateway")

        dns_values = [item for item in re.split(r"[,\s]+", str(result["dns"])) if item]
        result["dns"] = " ".join(self._validate_ipv4(item, "DNS server", True) for item in dns_values)
        return result

    def _configure_network(self, options: Mapping[str, object], log: LOG) -> None:
        static_ip = bool(options["static_ip"])

        def write_config() -> None:
            lines = [
                "[Match]",
                f"Name={self.NETWORK_INTERFACE}",
                "",
                "[Network]",
            ]
            if static_ip:
                lines.extend(
                    [
                        f"Address={options['ip_address']}/{options['prefix_length']}",
                    ]
                )
                if options["gateway"]:
                    lines.append(f"Gateway={options['gateway']}")
                if options["dns"]:
                    for dns_server in str(options["dns"]).split():
                        lines.append(f"DNS={dns_server}")
            else:
                lines.append("DHCP=yes")
            self.NETWORK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            self.NETWORK_CONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8")

            if self.DHCPCD_CONFIG.exists():
                existing = self.DHCPCD_CONFIG.read_text(encoding="utf-8")
                cleaned: List[str] = []
                in_managed_block = False
                for line in existing.splitlines():
                    if line.strip() == self.NETWORK_BLOCK_BEGIN:
                        in_managed_block = True
                        continue
                    if line.strip() == self.NETWORK_BLOCK_END:
                        in_managed_block = False
                        continue
                    if not in_managed_block:
                        cleaned.append(line)
                self.DHCPCD_CONFIG.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")

        self._try(
            "writing static IPv4 configuration" if static_ip else "removing static IPv4 configuration",
            write_config,
            log,
        )
        self._service("dhcpcd.service", False, log)
        self._service("systemd-networkd.service", True, log)
        self._try(
            "applying Ethernet network configuration",
            lambda: self.runner.run(["systemctl", "restart", "systemd-networkd.service"]),
            log,
        )

    def _service(self, service: str, enabled: bool, log: LOG) -> None:
        verb = "enable" if enabled else "disable"
        args = ["systemctl", verb, "--now", service]
        self._try(f"{verb} {service}", lambda: self.runner.run(args), log)

    def _set_services(self, options: Mapping[str, object], log: LOG) -> None:
        if self.variant == "minimal":
            self._service("snapclient.service", True, log)
            return

        if self.variant == "base":
            desired = {
                "snapserver.service": options["snapserver"],
                "snapclient.service": options["snapclient"],
                "mysqld.service": True,
            }
            desired.update({service: options["webserver"] for service in self.WEB_SERVICES})
            desired["docker.service"] = options["jellyfin"]
            desired.update({service: False for service in self.COMMON_DISABLED})
            for service, enabled in desired.items():
                self._service(service, enabled, log)
            return

        desired = {
            "start.service": options["gui"],
            "startup.service": not options["gui"],
            "snapserver.service": options["snapserver"],
            "snapclient.service": options["snapclient"],
            "mysqld.service": True,
            "psplash-start.service": options["gui"],
            "psplash-quit.service": options["gui"],
        }
        desired.update({service: options["webserver"] for service in self.WEB_SERVICES})
        desired["docker.service"] = options["jellyfin"]
        desired.update({service: False for service in self.COMMON_DISABLED})
        for service, enabled in desired.items():
            self._service(service, enabled, log)

    def _configure_common(self, options: Mapping[str, object], log: LOG) -> None:
        self._try(
            "setting vm.swappiness=0",
            self._set_swappiness,
            log,
        )
        self._try(
            "setting Master volume to 100%",
            lambda: self.runner.run(["amixer", "sset", "Master", "100%"]),
            log,
        )
        if options["gui"]:
            self._try(
                "disabling the PulseAudio HDMI profile",
                lambda: self.runner.run(
                    ["pactl", "set-card-profile", "alsa_card.platform-bcm2835_audio", "off"]
                ),
                log,
            )
            for path in (
                Path("/etc/mediaserver/alarm.sh"),
                Path("/etc/mediaserver/youtubedl.ini"),
                Path("/usr/lib/systemd/system/alarm.timer"),
                Path("/lib/systemd/system/alarm.timer"),
            ):
                if path.exists():
                    self._try(
                        f"setting group www-data: {path}",
                        lambda path=path: self.runner.run(["chgrp", "www-data", str(path)]),
                        log,
                    )
            ini_file = Path("/etc/mediaserver/youtubedl.ini")
            if ini_file.exists():
                self._try(
                    "granting write permissions to youtubedl.ini",
                    lambda: self.runner.run(["chmod", "775", str(ini_file)]),
                    log,
                )

    @staticmethod
    def _set_swappiness() -> None:
        path = Path("/etc/sysctl.conf")
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        replacement = "vm.swappiness=0"
        found = False
        output: List[str] = []
        for line in lines:
            if re.match(r"^\s*#?\s*vm\.swappiness\s*=", line):
                if not found:
                    output.append(replacement)
                    found = True
            else:
                output.append(line)
        if not found:
            output.append(replacement)
        path.write_text("\n".join(output) + "\n", encoding="utf-8")

    def _configure_vim(self, log: LOG) -> None:
        target = Path("/home/root/.vim/bundle/Vundle.vim")
        if target.exists():
            log("OK: VIM/Vundle is already configured")
            return
        self._try(
            "installing Vundle for VIM",
            lambda: self._clone_vundle(target),
            log,
        )

    def _clone_vundle(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        self.runner.run(["git", "clone", "https://github.com/VundleVim/Vundle.vim.git", str(target)])

    def _configure_jellyfin(self, log: LOG) -> None:
        docker = shutil.which("docker") or "docker"
        try:
            inspect = self.runner.run([docker, "container", "inspect", "jellyfin"], check=False)
        except CommandError as exc:
            log(f"WARNING: checking the Jellyfin container: {exc}")
            return
        if inspect.returncode == 0:
            self._try("starting the Jellyfin container", lambda: self.runner.run([docker, "start", "jellyfin"]), log)
            return

        def create() -> None:
            Path("/etc/Jellyfin/config").mkdir(parents=True, exist_ok=True)
            Path("/etc/Jellyfin/cache").mkdir(parents=True, exist_ok=True)
            self.runner.run([docker, "pull", "jellyfin/jellyfin"])
            self.runner.run(
                [
                    docker,
                    "run",
                    "-d",
                    "--name",
                    "jellyfin",
                    "--volume",
                    "/etc/Jellyfin/config:/config",
                    "--volume",
                    "/etc/Jellyfin/cache:/cache",
                    "--volume",
                    "/home:/home_media",
                    "--volume",
                    "/mnt:/external_media",
                    "--net=host",
                    "--restart=unless-stopped",
                    "jellyfin/jellyfin",
                ]
            )

        self._try("creating the Jellyfin container", create, log)

    def _stop_jellyfin(self, log: LOG) -> None:
        docker = shutil.which("docker") or "docker"
        try:
            inspect = self.runner.run([docker, "container", "inspect", "jellyfin"], check=False)
        except CommandError:
            return
        if inspect.returncode == 0:
            self._try("stopping the unused Jellyfin container", lambda: self.runner.run([docker, "stop", "jellyfin"]), log)

    def _install_bootstrap_assets(self, log: LOG) -> None:
        destinations = [
            Path("/usr/htdocs"),
            Path("/opt/youtubedl-web/youtubedlWeb/static"),
        ]
        for destination in destinations:
            if not destination.exists():
                continue
            self._try(
                f"installing Bootstrap and Clockpicker in {destination}",
                lambda destination=destination: self._download_assets(destination),
                log,
            )

    def _download_assets(self, destination: Path) -> None:
        bootstrap_dir = destination / "bootstrap-5.0.0"
        if not bootstrap_dir.exists():
            with tempfile.NamedTemporaryFile(suffix=".zip") as archive:
                urllib.request.urlretrieve(self.BOOTSTRAP_URL, archive.name)
                self._safe_extract(archive.name, destination, "bootstrap-5.0.0-beta1-dist")
            extracted = destination / "bootstrap-5.0.0-beta1-dist"
            if extracted.exists():
                extracted.rename(bootstrap_dir)
        if destination == Path("/opt/youtubedl-web/youtubedlWeb/static") and not (destination / "clockpicker").exists():
            with tempfile.NamedTemporaryFile(suffix=".zip") as archive:
                urllib.request.urlretrieve(self.CLOCKPICKER_URL, archive.name)
                self._safe_extract(archive.name, destination, "clockpicker-gh-pages")
            extracted = destination / "clockpicker-gh-pages"
            if extracted.exists():
                extracted.rename(destination / "clockpicker")

    @staticmethod
    def _safe_extract(archive: str, destination: Path, top_level: str) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                member_path = Path(member.filename)
                if not member_path.parts or member_path.parts[0] != top_level:
                    continue
                target = (destination / member.filename).resolve()
                if destination.resolve() not in target.parents and target != destination.resolve():
                    raise ValueError(f"niebezpieczna ścieżka w archiwum: {member.filename}")
                zipped.extract(member, destination)

    def _save_state(self, mode: str, hostname: str, options: Mapping[str, object], log: LOG) -> None:
        payload = {
            "mode": mode,
            "hostname": hostname,
            "options": dict(options),
        }

        def save() -> None:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(self.STATE_FILE.parent), delete=False
            ) as temporary:
                json.dump(payload, temporary, indent=2, sort_keys=True)
                temporary.write("\n")
                temporary_name = temporary.name
            os.chmod(temporary_name, 0o644)
            os.replace(temporary_name, self.STATE_FILE)

        self._try("saving the selected mode", save, log)

