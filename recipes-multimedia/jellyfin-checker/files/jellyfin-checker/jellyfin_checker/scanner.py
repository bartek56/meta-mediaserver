"""Recursive media file discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .ffprobe import probe_file


SUPPORTED_EXTENSIONS = frozenset({
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".m4v",
    ".ts",
    ".m2ts",
    ".webm",
})


def iter_media_files(path: str | Path) -> Iterator[Path]:
    root = Path(path)
    if root.is_file():
        if root.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield root
        return
    if not root.is_dir():
        raise FileNotFoundError(root)
    for candidate in sorted(root.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield candidate


def scan(path: str | Path, ffprobe_bin: str = "ffprobe") -> Iterator[dict]:
    """Yield metadata for supported media files without modifying them."""

    for media_path in iter_media_files(path):
        yield probe_file(media_path, ffprobe_bin=ffprobe_bin)

