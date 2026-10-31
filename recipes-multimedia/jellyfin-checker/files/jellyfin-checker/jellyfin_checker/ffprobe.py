"""FFprobe integration and metadata normalisation.

The checker only reads media metadata.  FFprobe is never asked to write to
the input file and the subprocess is run with a read-only set of options.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class FFProbeError(RuntimeError):
    """Raised when FFprobe cannot inspect a media file."""


def _hdr_info(stream: dict[str, Any]) -> dict[str, Any]:
    transfer = stream.get("color_transfer")
    side_data = stream.get("side_data_list") or []
    side_data_types = [item.get("side_data_type") for item in side_data if isinstance(item, dict)]

    hdr_type = None
    if transfer == "smpte2084" or any("Mastering display" in str(item) for item in side_data_types):
        hdr_type = "hdr10"
    elif transfer == "arib-std-b67":
        hdr_type = "hlg"
    elif any("Dolby Vision" in str(item) for item in side_data_types):
        hdr_type = "dolby_vision"

    return {
        "is_hdr": hdr_type is not None,
        "type": hdr_type,
        "color_transfer": transfer,
        "color_primaries": stream.get("color_primaries"),
        "color_space": stream.get("color_space"),
        "mastering_display_metadata": any(
            "Mastering display" in str(item) for item in side_data_types
        ),
        "content_light_level": any(
            "Content light level" in str(item) for item in side_data_types
        ),
        "side_data_types": side_data_types,
    }


def _stream_metadata(stream: dict[str, Any]) -> dict[str, Any]:
    tags = stream.get("tags") or {}
    metadata = {
        "index": stream.get("index"),
        "codec_name": stream.get("codec_name"),
        "codec_long_name": stream.get("codec_long_name"),
        "codec_type": stream.get("codec_type"),
        "profile": stream.get("profile"),
        "level": stream.get("level"),
        "codec_tag_string": stream.get("codec_tag_string"),
        "codec_tag": stream.get("codec_tag"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "coded_width": stream.get("coded_width"),
        "coded_height": stream.get("coded_height"),
        "pix_fmt": stream.get("pix_fmt"),
        "bits_per_raw_sample": stream.get("bits_per_raw_sample"),
        "bit_rate": stream.get("bit_rate"),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "r_frame_rate": stream.get("r_frame_rate"),
        "sample_aspect_ratio": stream.get("sample_aspect_ratio"),
        "display_aspect_ratio": stream.get("display_aspect_ratio"),
        "color_space": stream.get("color_space"),
        "color_transfer": stream.get("color_transfer"),
        "color_primaries": stream.get("color_primaries"),
        "chroma_location": stream.get("chroma_location"),
        "field_order": stream.get("field_order"),
        "sample_rate": stream.get("sample_rate"),
        "channels": stream.get("channels"),
        "channel_layout": stream.get("channel_layout"),
        "sample_fmt": stream.get("sample_fmt"),
        "language": tags.get("language"),
        "title": tags.get("title"),
        "disposition": dict(stream.get("disposition") or {}),
        "tags": dict(tags),
    }
    if stream.get("codec_type") == "video":
        metadata["hdr"] = _hdr_info(stream)
        metadata["side_data_list"] = stream.get("side_data_list") or []
    return metadata


def parse_ffprobe(data: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    """Convert FFprobe's JSON response into the checker's stable schema."""

    streams = data.get("streams") or []
    result: dict[str, Any] = {
        "path": str(path) if path is not None else data.get("path"),
        "video": [],
        "audio": [],
        "subtitles": [],
        "container": {},
        "ffprobe": {"stream_count": len(streams)},
    }

    for stream in streams:
        metadata = _stream_metadata(stream)
        kind = stream.get("codec_type")
        if kind == "video":
            result["video"].append(metadata)
        elif kind == "audio":
            result["audio"].append(metadata)
        elif kind == "subtitle":
            result["subtitles"].append(metadata)

    fmt = data.get("format") or {}
    result["container"] = {
        "format_name": fmt.get("format_name"),
        "format_long_name": fmt.get("format_long_name"),
        "duration": fmt.get("duration"),
        "size": fmt.get("size"),
        "bit_rate": fmt.get("bit_rate"),
        "tags": dict(fmt.get("tags") or {}),
    }
    return result


def parse_ffprobe_output(output: str, path: str | Path | None = None) -> dict[str, Any]:
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise FFProbeError(f"Invalid FFprobe JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FFProbeError("FFprobe response must be a JSON object")
    return parse_ffprobe(data, path)


def probe_file(path: str | Path, ffprobe_bin: str = "ffprobe") -> dict[str, Any]:
    """Run FFprobe for *path* and return normalised metadata."""

    media_path = Path(path)
    command = [
        ffprobe_bin,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-print_format",
        "json",
        str(media_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise FFProbeError(f"Cannot execute {ffprobe_bin}: {exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()
        raise FFProbeError(f"FFprobe failed for {media_path}: {detail or completed.returncode}")
    return parse_ffprobe_output(completed.stdout, media_path)

