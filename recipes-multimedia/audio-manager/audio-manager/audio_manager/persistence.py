"""Persistence of the active remote-device state."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG = logging.getLogger("audio-manager.persistence")


class ActiveClientsStore:
    """Write active device snapshots atomically for MPD and other readers."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._last_payload: str | None = None

    def publish(self, payload: dict[str, Any]) -> bool:
        """Persist a snapshot and return whether the file content changed.

        Args:
            payload: Registry payload without the generated timestamp.

        Returns:
            ``True`` when a new file was installed, otherwise ``False``.

        Raises:
            OSError: If the destination directory or file cannot be written.
        """

        document = dict(payload)
        document["generated_at"] = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(document, indent=2, sort_keys=True) + "\n"

        # The timestamp is intentionally ignored when deciding whether the
        # externally visible state changed.
        comparable = dict(document)
        comparable.pop("generated_at", None)
        comparable_text = json.dumps(comparable, sort_keys=True)
        if self._last_payload == comparable_text and self._path.exists():
            LOG.debug("Active client state is unchanged")
            return False

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.chmod(temporary_path, 0o644)
            os.replace(temporary_path, self._path)
        except OSError:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except OSError:
                    pass
            LOG.exception("Could not atomically write active client state to %s", self._path)
            raise

        self._last_payload = comparable_text
        LOG.info("Updated active client state: %d client(s)", len(document.get("clients", [])))
        return True
