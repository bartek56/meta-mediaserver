"""Domain models used by the audio manager.

The models deliberately do not import D-Bus, PulseAudio, Snapcast, or any
other system integration.  This makes state transitions deterministic and
straightforward to test on a development machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ServiceKind(str, Enum):
    """A service advertised by a remote device."""

    SNAPCLIENT = "snapclient"
    PULSE_AUDIO = "pulse"


class HostStatus(str, Enum):
    """Reachability state obtained from the ICMP monitor."""

    WAITING_FOR_ADDRESS = "waiting_for_address"
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ServiceStatus(str, Enum):
    """State of a service probe."""

    UNKNOWN = "unknown"
    ACTIVE = "active"
    INACTIVE = "inactive"
    STALE = "stale"


@dataclass(frozen=True, order=True)
class ServiceKey:
    """Identify one Avahi service instance and interface."""

    kind: ServiceKind
    interface: int
    protocol: int
    instance: str


@dataclass
class ServiceRecord:
    """Resolved information for one advertised service."""

    key: ServiceKey
    port: int
    addresses: set[str] = field(default_factory=set)


@dataclass
class DeviceState:
    """Aggregated state for one remote device.

    A device can advertise PulseAudio and Snapclient independently.  Removing
    one service therefore does not remove the other service or its monitor.
    """

    device_id: str
    display_name: str
    hostname: str
    services: dict[ServiceKey, ServiceRecord] = field(default_factory=dict)
    host_status: HostStatus = HostStatus.WAITING_FOR_ADDRESS
    ping_failures: int = 0
    pulse_status: ServiceStatus = ServiceStatus.UNKNOWN
    snapclient_status: ServiceStatus = ServiceStatus.UNKNOWN
    pulse_failure_count: int = 0
    snapclient_failure_count: int = 0
    last_seen_sec: int | None = None

    def has_service(self, kind: ServiceKind) -> bool:
        """Return whether the device currently advertises ``kind``."""

        return any(record.key.kind is kind for record in self.services.values())

    def endpoints(self, kind: ServiceKind | None = None) -> tuple[str, ...]:
        """Return sorted IPv4/IPv6 addresses known for this device."""

        addresses: set[str] = set()
        for record in self.services.values():
            if kind is None or record.key.kind is kind:
                addresses.update(record.addresses)
        return tuple(sorted(addresses))

    def port(self, kind: ServiceKind, default: int) -> int:
        """Return the first advertised port for ``kind`` or ``default``."""

        for record in self.services.values():
            if record.key.kind is kind:
                return record.port
        return default

    def to_json(self) -> dict[str, Any]:
        """Convert the state to the public active-clients JSON structure."""

        return {
            "id": self.device_id,
            "display_name": self.display_name,
            "hostname": self.hostname,
            "addresses": list(self.endpoints()),
            "host": {
                "active": self.host_status is HostStatus.AVAILABLE,
            },
            "pulse": {
                "active": self.pulse_status is ServiceStatus.ACTIVE,
                "port": self.port(ServiceKind.PULSE_AUDIO, 4713),
            },
            "snapclient": {
                "active": self.snapclient_status is ServiceStatus.ACTIVE,
                "port": self.port(ServiceKind.SNAPCLIENT, 1704),
            },
        }


def device_identity(kind: ServiceKind, instance: str) -> tuple[str, str]:
    """Return a stable device identifier and display name from an Avahi name.

    Snapclient services are normally named ``Snapclient-<name>`` and
    PulseAudio services are normally named ``pulse@<name>``.  The prefixes are
    removed so both advertisements map to one device record.
    """

    value = instance.strip().rstrip(".")
    lowered = value.lower()
    prefixes = {
        ServiceKind.SNAPCLIENT: "snapclient-",
        ServiceKind.PULSE_AUDIO: "pulse@",
    }
    prefix = prefixes[kind]
    if lowered.startswith(prefix):
        value = value[len(prefix) :]
    value = value.rstrip(".") or "unknown"
    return value.lower(), value
