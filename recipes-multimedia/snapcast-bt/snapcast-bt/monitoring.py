#!/usr/bin/python3

"""Common service-monitoring primitives for audio-manager."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import subprocess
import time
from typing import Any, Iterable

import pulsectl


@dataclass(frozen=True)
class MonitoringResult:
    """Result of one monitoring observation."""

    available: bool | None
    changed: bool
    consecutive_failures: int
    reason: str | None = None


class MonitoringInterface(ABC):
    """Common state machine for one monitored service or device.

    A monitor performs one observation at a time. ``None`` means that the
    observation could not be made and must not change the current state. A
    failed observation increments the consecutive-failure counter and changes
    the service to unavailable only after ``failure_threshold`` failures.
    """

    def __init__(self, failure_threshold: int = 1) -> None:
        """Initialize the state machine with a consecutive-failure threshold."""
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        self.failure_threshold = failure_threshold
        self.available: bool | None = None
        self.consecutive_failures = 0

    @abstractmethod
    def probe(self) -> bool | None:
        """Perform one service-specific observation."""

    def check(self) -> MonitoringResult:
        """Run one probe and convert its result into a state transition."""
        return self.observe(self.probe())

    def reset(self) -> None:
        """Forget the previous state after the monitored object is rediscovered."""
        self.available = None
        self.consecutive_failures = 0

    def observe(
        self,
        available: bool | None,
        reason: str | None = None,
    ) -> MonitoringResult:
        """Apply an observation without changing state for an unknown result."""
        previous = self.available
        if available is None:
            return MonitoringResult(
                available=self.available,
                changed=False,
                consecutive_failures=self.consecutive_failures,
                reason=reason,
            )

        if available:
            self.consecutive_failures = 0
            self.available = True
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.failure_threshold:
                self.available = False

        return MonitoringResult(
            available=self.available,
            changed=self.available != previous,
            consecutive_failures=self.consecutive_failures,
            reason=reason,
        )


class PingMonitor(MonitoringInterface):
    """Monitor a device with one ``ping -c 1`` attempt per check."""

    def __init__(
        self,
        addresses: Iterable[str] = (),
        timeout: float = 1.0,
        failure_threshold: int = 3,
    ) -> None:
        """Configure one-ping checks and the offline failure threshold."""
        super().__init__(failure_threshold=failure_threshold)
        self.addresses = set(str(address) for address in addresses)
        self.timeout = timeout
        self.last_address: str | None = None
        self.last_reason: str | None = None

    def set_addresses(self, addresses: Iterable[str]) -> None:
        """Replace the currently known IPv4 targets for the device."""
        self.addresses = set(str(address) for address in addresses)

    def probe(self) -> bool | None:
        """Send exactly one ICMP echo request to the selected address."""
        if not self.addresses:
            self.last_address = None
            self.last_reason = "no IPv4 address available"
            return None

        wait_seconds = max(1, math.ceil(self.timeout))
        process_timeout = max(self.timeout + 0.5, 1.5)
        # One monitor check is deliberately one ICMP echo request.  The
        # failure threshold, rather than ``ping -c``, decides when the device
        # is declared unavailable.
        address = sorted(self.addresses)[0]
        self.last_address = address
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(wait_seconds), address],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=process_timeout,
            )
        except subprocess.TimeoutExpired:
            self.last_reason = f"ping timeout for {address}"
            return False
        except OSError as exc:
            self.last_reason = f"ping execution failed for {address}: {exc}"
            return False
        self.last_reason = f"ping {address} exit={result.returncode}"
        return result.returncode == 0

    def check(self) -> MonitoringResult:
        """Return the ping result together with its command-level explanation."""
        return self.observe(self.probe(), self.last_reason)


class PulseAudioMonitor(MonitoringInterface):
    """Verify a remote PulseAudio native-protocol handshake."""

    def __init__(
        self,
        addresses: Iterable[str] = (),
        port: int = 4713,
        timeout: float = 1.0,
        failure_threshold: int = 1,
    ) -> None:
        """Configure native PulseAudio handshake parameters."""
        super().__init__(failure_threshold=failure_threshold)
        self.addresses = set(str(address) for address in addresses)
        self.port = port
        self.timeout = timeout
        self.last_reason: str | None = None

    def set_addresses(self, addresses: Iterable[str]) -> None:
        """Replace the remote PulseAudio addresses used by the next probe."""
        self.addresses = set(str(address) for address in addresses)

    def probe(self) -> bool | None:
        """Connect to each known PulseAudio endpoint until one handshakes."""
        if not self.addresses:
            self.last_reason = "no IPv4 address available"
            return None

        for address in sorted(self.addresses):
            pulse: Any | None = None
            try:
                pulse = pulsectl.Pulse(
                    "audio-manager-probe",
                    server=f"tcp:{address}:{self.port}",
                    connect=False,
                )
                pulse.connect(autospawn=False, timeout=self.timeout)
                pulse.server_info()
                self.last_reason = f"PulseAudio handshake succeeded for {address}"
                return True
            except Exception as exc:
                self.last_reason = f"PulseAudio handshake failed for {address}: {exc}"
                continue
            finally:
                if pulse is not None:
                    try:
                        pulse.close()
                    except Exception:
                        pass
        return False

    def check(self) -> MonitoringResult:
        """Return the handshake result and the last connection error/success."""
        return self.observe(self.probe(), self.last_reason)


class SnapcastMonitor(MonitoringInterface):
    """Evaluate one Snapclient from a ``Server.GetStatus`` record."""

    def __init__(self, last_seen_timeout: float = 5.0) -> None:
        """Configure the maximum accepted age of a Snapclient lastSeen value."""
        super().__init__(failure_threshold=1)
        self.last_seen_timeout = last_seen_timeout

    def probe(self) -> bool | None:
        """Reject direct probing because Snapcast status is supplied externally."""
        raise RuntimeError("SnapcastMonitor requires observe_client()")

    def observe_client(
        self,
        client: dict[str, Any] | None,
        now: float | None = None,
    ) -> MonitoringResult:
        """Evaluate one Snapclient status record from Server.GetStatus."""
        if client is None:
            return self.observe(False, "client not present in Server.GetStatus")

        if now is None:
            now = time.time()
        last_seen = client.get("lastSeen", {})
        last_seen_seconds = last_seen.get("sec")
        if client.get("connected") is not True or not isinstance(
            last_seen_seconds, (int, float)
        ):
            return self.observe(False, "Snapclient is disconnected or has no lastSeen")

        age = max(0.0, now - float(last_seen_seconds))
        if age >= self.last_seen_timeout:
            return self.observe(False, f"lastSeen is {age:.1f}s old")
        return self.observe(True, f"lastSeen is {age:.1f}s old")
