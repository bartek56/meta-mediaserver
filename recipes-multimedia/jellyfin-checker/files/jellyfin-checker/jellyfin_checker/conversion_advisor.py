"""Generate non-executed, minimal FFmpeg recommendations."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any, Iterable


TEXT_SUBTITLE_CODECS = frozenset({
    "ass",
    "ssa",
    "subrip",
    "srt",
    "webvtt",
    "mov_text",
})


def _quote(value: str) -> str:
    return shlex.quote(str(value))


def _text_subtitle_maps(media: dict[str, Any]) -> tuple[list[str], bool]:
    """Return MP4-safe subtitle maps and whether any subtitle was omitted."""

    maps: list[str] = []
    omitted = False
    for position, subtitle in enumerate(media.get("subtitles") or []):
        codec = str(subtitle.get("codec_name") or "").lower()
        stream_index = subtitle.get("index", position)
        if codec in TEXT_SUBTITLE_CODECS:
            maps.extend(["-map", f"0:{stream_index}"])
        else:
            omitted = True
    return maps, omitted


def recommendations_for(media: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, str]]:
    problems = analysis.get("problems") or []
    hard_problems = [problem for problem in problems if problem.get("status") == "UNSUPPORTED"]
    if not hard_problems:
        if analysis.get("result") in {"UNKNOWN", "CONDITIONAL"}:
            return [{
                "reason": "verification",
                "command": "",
                "note": "Verify the conditional or unknown rule on the target device before converting media.",
            }]
        return []

    source = str(media.get("path") or "input")
    source_path = Path(source)
    has_video = any(problem.get("component") == "video" for problem in hard_problems)
    has_audio = any(problem.get("component") == "audio" for problem in hard_problems)
    has_subtitles = any(problem.get("component") == "subtitle" for problem in hard_problems)
    has_container = any(problem.get("component") == "container" for problem in hard_problems)

    target_extension = "mp4"
    target = source_path.with_name(f"{source_path.stem}.compatible.{target_extension}")
    input_arg = _quote(source)
    output_arg = _quote(str(target))
    subtitle_maps, omitted_subtitles = _text_subtitle_maps(media)
    parts = ["ffmpeg", "-i", input_arg, "-map", "0:v?", "-map", "0:a?"]
    parts.extend(subtitle_maps)
    if has_video:
        parts.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"])
    else:
        parts.extend(["-c:v", "copy"])
    if has_audio:
        parts.extend(["-c:a", "aac", "-b:a", "384k"])
    else:
        parts.extend(["-c:a", "copy"])
    if subtitle_maps:
        parts.extend(["-c:s", "mov_text"])
    parts.append(output_arg)

    reasons = []
    if has_video:
        reasons.append("video")
    if has_audio:
        reasons.append("audio")
    if has_subtitles:
        reasons.append("subtitle")
    if has_container:
        reasons.append("container")
    note = "This is a recommendation only; the original file is not modified and FFmpeg is not started."
    if omitted_subtitles:
        note += " Bitmap or otherwise unsupported subtitle streams are omitted from the MP4 recommendation."
    return [{
        "reason": ", ".join(reasons),
        "command": " ".join(parts),
        "note": note,
    }]


def add_recommendations(media: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    result = dict(analysis)
    result["recommendations"] = recommendations_for(media, analysis)
    return result


def write_recommendations(results: Iterable[dict[str, Any]], path: str | Path) -> None:
    lines: list[str] = []
    for item in results:
        media = item.get("media") or {}
        lines.append(f"Movie: {media.get('path', '<unknown>')}")
        lines.append(f"Profile: {item.get('profile_name', item.get('profile_id', '<unknown>'))}")
        lines.append(f"Result: {item.get('result', '<unknown>')}")
        for recommendation in item.get("recommendations", []):
            lines.append(f"Reason: {recommendation.get('reason', '')}")
            if recommendation.get("command"):
                lines.append(f"FFmpeg: {recommendation['command']}")
            lines.append(f"Note: {recommendation.get('note', '')}")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")

