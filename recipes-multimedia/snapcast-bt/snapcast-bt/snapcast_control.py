#!/usr/bin/python3

"""Snapcast JSON-RPC and group stream control."""

from __future__ import annotations

import json
import logging
import socket
from typing import Any


class SnapcastControl:
    """Small synchronous client for the local Snapserver control socket."""

    def __init__(
        self,
        host: str,
        port: int,
        stream_names: dict[str, str],
        logger: logging.Logger,
    ) -> None:
        """Configure the JSON-RPC endpoint and logical stream names."""
        self.host = host
        self.port = port
        self.stream_names = stream_names
        self.logger = logger

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send one newline-delimited JSON-RPC request and decode its response."""
        request: dict[str, Any] = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            request["params"] = params
        self.logger.debug("Snapcast JSON-RPC request: method=%s", method)
        with socket.create_connection((self.host, self.port), timeout=1.0) as connection:
            connection.sendall((json.dumps(request) + "\n").encode())
            data = b""
            while b"\n" not in data:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data += chunk
        response = json.loads(data.splitlines()[0].decode())
        self.logger.debug(
            "Snapcast JSON-RPC response: method=%s has_error=%s",
            method,
            "error" in response,
        )
        return response

    def set_stream(self, mode: str) -> bool:
        """Set the requested stream on every Snapcast group that needs it."""
        stream = self.stream_names.get(mode)
        if stream is None:
            self.logger.debug("Ignoring unknown Snapcast source mode: %s", mode)
            return False
        try:
            status = self.request("Server.GetStatus")
            groups = status["result"]["server"]["groups"]
            groups_to_update = [
                group for group in groups if group.get("stream_id") != stream
            ]
            self.logger.debug(
                "Snapcast stream decision: mode=%s stream=%s groups=%d updates=%d",
                mode,
                stream,
                len(groups),
                len(groups_to_update),
            )
            for group in groups_to_update:
                self.request(
                    "Group.SetStream",
                    {"id": group["id"], "stream_id": stream},
                )
            return bool(groups)
        except (OSError, ValueError, KeyError, socket.timeout) as exc:
            self.logger.warning("Snapcast control API unavailable: %s", exc)
            return False
