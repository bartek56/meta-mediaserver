"""Events exchanged between system adapters and the application loop."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ServiceKey, ServiceKind


@dataclass(frozen=True)
class ServiceDiscovered:
    """An Avahi browser reported a new service instance."""

    key: ServiceKey
    port: int


@dataclass(frozen=True)
class ServiceResolved:
    """An Avahi resolver returned an address for a service."""

    key: ServiceKey
    address: str
    port: int


@dataclass(frozen=True)
class ServiceRemoved:
    """An Avahi browser removed a service instance."""

    key: ServiceKey


@dataclass(frozen=True)
class SystemdStateChanged:
    """systemd reported a new ActiveState for a unit."""

    unit_name: str
    active: bool


@dataclass(frozen=True)
class PingCompleted:
    """A device ping completed in a worker thread."""

    device_id: str
    success: bool
    address: str | None


@dataclass(frozen=True)
class PulseProbeCompleted:
    """A remote PulseAudio handshake completed in a worker thread."""

    device_id: str
    success: bool


@dataclass(frozen=True)
class SnapcastStatusCompleted:
    """A local Snapcast status request completed."""

    status: dict


@dataclass(frozen=True)
class ProbeFailed:
    """A worker could not complete a probe."""

    probe_name: str
    device_id: str | None
    error: str
