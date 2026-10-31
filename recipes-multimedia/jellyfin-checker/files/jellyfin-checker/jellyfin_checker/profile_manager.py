"""Profile loading, inheritance and controlled official-source updates."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


STATUSES = {"SUPPORTED", "CONDITIONAL", "UNSUPPORTED", "UNKNOWN"}


def status_from_rule(rule: Any) -> str:
    """Read both the current ``status`` form and the initial ``supported`` form."""

    if isinstance(rule, dict):
        status = rule.get("status")
        if isinstance(status, str) and status.upper() in STATUSES:
            return status.upper()
        if "supported" in rule:
            return "SUPPORTED" if rule["supported"] is True else "UNSUPPORTED"
    if isinstance(rule, str) and rule.upper() in STATUSES:
        return rule.upper()
    return "UNKNOWN"


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _json_files(directory: Path) -> Iterable[Path]:
    if not directory.is_dir():
        return ()
    return sorted(directory.glob("*.json"))


class ProfileManager:
    """Resolve built-in profiles and user overrides.

    Built-in profiles are read-only.  Device/custom profiles live below the
    user's configuration directory and can inherit a built-in profile.
    """

    def __init__(self, config_dir: str | Path | None = None, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent / "data"
        configured = config_dir or os.environ.get("JELLYFIN_CHECKER_CONFIG")
        self.config_dir = Path(configured).expanduser() if configured else Path.home() / ".config" / "jellyfin-checker"
        self.user_profiles_dir = self.config_dir / "profiles"

    def _candidate_paths(self, profile_id: str) -> list[Path]:
        return [
            self.user_profiles_dir / "devices" / f"{profile_id}.json",
            self.user_profiles_dir / "general" / f"{profile_id}.json",
            self.data_dir / "profiles" / "devices" / f"{profile_id}.json",
            self.data_dir / "profiles" / "general" / f"{profile_id}.json",
        ]

    def _raw_path(self, profile_id: str) -> Path:
        for path in self._candidate_paths(profile_id):
            if path.is_file():
                return path
        raise FileNotFoundError(f"Profile not found: {profile_id}")

    def load_raw(self, profile_id: str) -> dict[str, Any]:
        path = self._raw_path(profile_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read profile {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Profile {path} must contain a JSON object")
        value.setdefault("id", profile_id)
        return value

    def load(self, profile_id: str) -> dict[str, Any]:
        return self._resolve(profile_id, ())

    def _resolve(self, profile_id: str, chain: tuple[str, ...]) -> dict[str, Any]:
        if profile_id in chain:
            raise ValueError("Profile inheritance cycle: " + " -> ".join((*chain, profile_id)))
        raw = self.load_raw(profile_id)
        parent_id = raw.get("inherits")
        if parent_id:
            merged = deep_merge(self._resolve(str(parent_id), (*chain, profile_id)), raw)
        else:
            merged = copy.deepcopy(raw)

        manual_overrides = merged.pop("manual_overrides", {})
        explicit_overrides = merged.pop("overrides", {})
        if isinstance(explicit_overrides, dict):
            merged = deep_merge(merged, explicit_overrides)
        if isinstance(manual_overrides, dict):
            merged = deep_merge(merged, manual_overrides)
        merged.pop("inherits", None)
        merged["id"] = raw.get("id", profile_id)
        return merged

    def list_profiles(self) -> list[dict[str, Any]]:
        paths: dict[str, Path] = {}
        for root in (
            self.data_dir / "profiles" / "general",
            self.data_dir / "profiles" / "devices",
            self.user_profiles_dir / "general",
            self.user_profiles_dir / "devices",
        ):
            for path in _json_files(root):
                paths[path.stem] = path

        profiles = []
        for profile_id, path in sorted(paths.items()):
            try:
                profile = self.load(profile_id)
                profiles.append({
                    "id": profile_id,
                    "name": profile.get("name", profile_id),
                    "type": profile.get("type", "unknown"),
                    "path": str(path),
                })
            except (OSError, ValueError) as exc:
                profiles.append({"id": profile_id, "name": f"Invalid profile: {exc}", "type": "invalid", "path": str(path)})
        return profiles

    def user_profile_path(self, profile_id: str, profile_type: str = "devices") -> Path:
        return self.user_profiles_dir / profile_type / f"{profile_id}.json"

    def prepare_edit(self, profile_id: str) -> Path:
        source = self._raw_path(profile_id)
        destination = self.user_profile_path(profile_id, "devices" if source.parent.name == "devices" else "general")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.resolve() != source.resolve():
            shutil.copyfile(source, destination)
        return destination

    def edit(self, profile_id: str) -> Path:
        path = self.prepare_edit(profile_id)
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
        if editor:
            subprocess.run([editor, str(path)], check=False)
        return path

    def update_official(self, profile_ids: Iterable[str] | None = None, timeout: int = 20) -> list[dict[str, Any]]:
        """Snapshot documented sources and report changes.

        The documentation is HTML and is intentionally not parsed into codec
        rules automatically.  This makes updates auditable and guarantees
        that a changed page cannot silently overwrite manual edits.
        """

        selected = list(profile_ids) if profile_ids else [item["id"] for item in self.list_profiles()]
        snapshot_dir = self.config_dir / "data" / "official" / "snapshots"
        state_path = self.config_dir / "data" / "official" / "source-state.json"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        state: dict[str, Any] = {}
        if state_path.is_file():
            try:
                loaded = json.loads(state_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    state = loaded
            except json.JSONDecodeError:
                state = {}

        changes: list[dict[str, Any]] = []
        for profile_id in selected:
            profile = self.load(profile_id)
            source = profile.get("source") or {}
            url = source.get("url")
            if not url:
                continue
            request = urllib.request.Request(str(url), headers={"User-Agent": "jellyfin-checker/0.1"})
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    content = response.read()
            except OSError as exc:
                changes.append({"profile": profile_id, "url": url, "error": str(exc)})
                continue

            digest = hashlib.sha256(content).hexdigest()
            old_digest = state.get(str(url), {}).get("sha256")
            changed = old_digest is not None and old_digest != digest
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            snapshot = snapshot_dir / f"{profile_id}-{timestamp}-{digest[:12]}.html"
            snapshot.write_bytes(content)
            state[str(url)] = {
                "profile": profile_id,
                "sha256": digest,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "snapshot": str(snapshot),
            }
            changes.append({
                "profile": profile_id,
                "url": url,
                "sha256": digest,
                "changed": changed,
                "snapshot": str(snapshot),
                "manual_rules_preserved": True,
            })

        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return changes

