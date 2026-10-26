#!/usr/bin/python3

"""Persistent active-client state used by audio-manager and MPD setup."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
import logging
import os
from pathlib import Path
import time
from typing import Any


class ActiveClientsStore:
    """Read and atomically write the active remote-client JSON document.

    The store owns the file format. The controller only supplies discovered
    services, addresses, and their current health state.
    """

    def __init__(
        self,
        path: Path,
        snapclient_prefix: str,
        logger: logging.Logger,
    ) -> None:
        """Configure the runtime state-file path and its service prefix."""
        self.path = path
        self.snapclient_prefix = snapclient_prefix
        self.logger = logger
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        snapclients: Iterable[str],
        pulse_servers: Iterable[str],
        service_addresses: Mapping[str, Iterable[str]],
        snapclient_addresses: Mapping[str, Iterable[str]],
        device_availability: Mapping[str, bool],
        snapclient_active: Mapping[str, bool],
        pulse_active: Mapping[str, bool],
    ) -> None:
        """Build and atomically publish the current remote-client document."""
        clients: dict[str, dict[str, Any]] = {}

        for service_name in snapclients:
            client_id = self._client_id_from_service(
                service_name,
                self.snapclient_prefix,
            )
            self._merge_service(
                clients,
                client_id,
                service_name,
                "snapclient",
                service_addresses,
                snapclient_addresses,
                device_availability,
                snapclient_active,
            )

        for service_name in pulse_servers:
            client_id = self._client_id_from_service(service_name, "pulse@")
            self._merge_service(
                clients,
                client_id,
                service_name,
                "pulse",
                service_addresses,
                snapclient_addresses,
                device_availability,
                pulse_active,
            )

        payload = {
            "schema": 1,
            "generated_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(),
            ),
            "clients": sorted(
                clients.values(),
                key=lambda item: item["id"].lower(),
            ),
        }
        temporary_path = self.path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, self.path)
        self.logger.debug(
            "Wrote active-client state: %s (%d clients)",
            self.path,
            len(payload["clients"]),
        )

    def read(self) -> dict[str, Any]:
        """Read and minimally validate the state file.

        A missing or malformed runtime file is represented as an empty state;
        stale data must never prevent discovery from starting again.
        """
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.logger.debug("Active-client state does not exist: %s", self.path)
            return self.empty_payload()
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.warning("Could not read active-client state %s: %s", self.path, exc)
            return self.empty_payload()
        if not isinstance(payload, dict) or not isinstance(payload.get("clients"), list):
            self.logger.warning("Invalid active-client state format: %s", self.path)
            return self.empty_payload()
        self.logger.debug(
            "Read active-client state: %s (%d clients)",
            self.path,
            len(payload["clients"]),
        )
        return payload

    @staticmethod
    def empty_payload() -> dict[str, Any]:
        """Return a valid empty state document for missing/corrupt files."""
        return {"schema": 1, "generated_at": None, "clients": []}

    def _merge_service(
        self,
        clients: dict[str, dict[str, Any]],
        client_id: str,
        service_name: str,
        service_key: str,
        service_addresses: Mapping[str, Iterable[str]],
        snapclient_addresses: Mapping[str, Iterable[str]],
        device_availability: Mapping[str, bool],
        service_active: Mapping[str, bool],
    ) -> None:
        """Merge one service into its device record and set its health flag."""
        client_key = client_id.lower()
        if not device_availability.get(client_key, True):
            self.logger.debug(
                "Not writing unavailable device %s to active-client state",
                client_id,
            )
            return

        addresses = set(service_addresses.get(service_name.lower(), ()))
        addresses.update(snapclient_addresses.get(client_key, ()))
        client = clients.setdefault(
            client_key,
            {
                "id": client_id,
                "hostname": f"{client_id}.local",
                "addresses": [],
                "pulse": {"active": False, "port": 4713},
                "snapclient": {"active": False, "port": 1704},
            },
        )
        client["addresses"] = sorted(
            set(client.get("addresses", [])) | addresses
        )
        client[service_key]["active"] = service_active.get(
            service_name.lower(),
            False,
        )
        self.logger.debug(
            "State service %s for %s: active=%s addresses=%s",
            service_key,
            client_id,
            client[service_key]["active"],
            sorted(addresses),
        )

    @staticmethod
    def _client_id_from_service(service_name: str, prefix: str) -> str:
        """Remove a discovery prefix from a service name."""
        value = str(service_name)
        if value.lower().startswith(prefix.lower()):
            return value[len(prefix):]
        return value
