"""The in-memory registry of discovered remote devices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    DeviceState,
    HostStatus,
    ServiceKey,
    ServiceKind,
    ServiceRecord,
    ServiceStatus,
    device_identity,
)


@dataclass(frozen=True)
class RegistryChange:
    """Describe a registry change that may require reconciliation."""

    device_id: str
    removed: bool = False


class DeviceRegistry:
    """Own all discovered devices and their independently monitored states."""

    def __init__(self) -> None:
        self._devices: dict[str, DeviceState] = {}
        self._service_devices: dict[ServiceKey, str] = {}

    def add_service(
        self,
        key: ServiceKey,
        port: int,
    ) -> RegistryChange:
        """Add an Avahi service without assuming that it is reachable.

        Args:
            key: Service identity supplied by Avahi.
            port: Port returned by service metadata, or the protocol default.

        Returns:
            A change identifying the device affected by the operation.
        """

        device_id, display_name = device_identity(key.kind, key.instance)
        device = self._devices.setdefault(
            device_id,
            DeviceState(
                device_id=device_id,
                display_name=display_name,
                hostname=(
                    display_name
                    if "." in display_name
                    else f"{display_name}.local"
                ),
            ),
        )
        device.services[key] = ServiceRecord(key=key, port=port)
        self._service_devices[key] = device_id
        if device.host_status is HostStatus.UNAVAILABLE:
            device.host_status = HostStatus.WAITING_FOR_ADDRESS
            device.ping_failures = 0
        return RegistryChange(device_id)

    def resolve_service(
        self,
        key: ServiceKey,
        address: str,
        port: int,
    ) -> RegistryChange | None:
        """Store a resolved address for an already discovered service."""

        device_id = self._service_devices.get(key)
        if device_id is None:
            return None
        record = self._devices[device_id].services.get(key)
        if record is None:
            return None
        record.addresses.add(address)
        record.port = port
        return RegistryChange(device_id)

    def remove_service(self, key: ServiceKey) -> RegistryChange | None:
        """Remove exactly one service and delete an empty device record."""

        device_id = self._service_devices.pop(key, None)
        if device_id is None:
            return None
        device = self._devices[device_id]
        device.services.pop(key, None)
        if not device.services:
            del self._devices[device_id]
            return RegistryChange(device_id, removed=True)
        return RegistryChange(device_id)

    def get(self, device_id: str) -> DeviceState | None:
        """Return a device by stable identifier."""

        return self._devices.get(device_id)

    def devices(self) -> tuple[DeviceState, ...]:
        """Return all currently discovered devices."""

        return tuple(self._devices.values())

    def update_host(
        self,
        device_id: str,
        status: HostStatus,
        failures: int,
    ) -> bool:
        """Update host state and return whether the public state changed."""

        device = self._devices.get(device_id)
        if device is None:
            return False
        changed = device.host_status is not status or device.ping_failures != failures
        device.host_status = status
        device.ping_failures = failures
        if status is HostStatus.UNAVAILABLE:
            device.pulse_status = ServiceStatus.UNKNOWN
            device.snapclient_status = ServiceStatus.UNKNOWN
            device.pulse_failure_count = 0
            device.snapclient_failure_count = 0
            device.last_seen_sec = None
        elif status is HostStatus.AVAILABLE and changed:
            device.pulse_status = ServiceStatus.UNKNOWN
            device.snapclient_status = ServiceStatus.UNKNOWN
            device.pulse_failure_count = 0
            device.snapclient_failure_count = 0
        return changed

    def update_pulse(
        self,
        device_id: str,
        status: ServiceStatus,
        failures: int,
    ) -> bool:
        """Update PulseAudio status and return whether it changed."""

        device = self._devices.get(device_id)
        if device is None:
            return False
        changed = device.pulse_status is not status or device.pulse_failure_count != failures
        device.pulse_status = status
        device.pulse_failure_count = failures
        return changed

    def update_snapclient(
        self,
        device_id: str,
        status: ServiceStatus,
        failures: int,
        last_seen_sec: int | None,
    ) -> bool:
        """Update Snapclient status and return whether it changed."""

        device = self._devices.get(device_id)
        if device is None:
            return False
        changed = (
            device.snapclient_status is not status
            or device.snapclient_failure_count != failures
            or device.last_seen_sec != last_seen_sec
        )
        device.snapclient_status = status
        device.snapclient_failure_count = failures
        device.last_seen_sec = last_seen_sec
        return changed

    def active_clients_payload(self) -> dict[str, Any]:
        """Build the atomically persisted state payload.

        Devices that do not answer ICMP are excluded from the active list.
        The service states inside an included device remain independent.
        """

        clients = [
            device.to_json()
            for device in self._devices.values()
            if device.host_status is HostStatus.AVAILABLE
        ]
        clients.sort(key=lambda item: str(item["id"]).lower())
        return {
            "schema": 1,
            "clients": clients,
        }
