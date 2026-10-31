"""Terminal, JSON and CSV report formatting."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from typing import Any, Iterable


def _problems_text(problems: list[dict[str, Any]]) -> str:
    return " | ".join(
        f"{item.get('component')}.{item.get('parameter')}: {item.get('message')}"
        for item in problems
    )


def make_report(media_items: Iterable[dict[str, Any]], analyses: Iterable[dict[str, Any]], errors: Iterable[dict[str, str]] = ()) -> dict[str, Any]:
    media_items = list(media_items)
    analyses = list(analyses)
    errors = list(errors)
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for analysis in analyses:
        by_path[str((analysis.get("media") or {}).get("path", ""))].append(analysis)

    summary = {
        "scanned_files": len(media_items),
        "supported_by_all_profiles": sum(
            1 for path_analyses in by_path.values()
            if path_analyses and all(item.get("result") == "DIRECT_PLAY" for item in path_analyses)
        ),
        "requiring_remux": sum(
            1 for path_analyses in by_path.values()
            if any(any(problem.get("component") == "container" for problem in item.get("problems", [])) for item in path_analyses)
        ),
        "requiring_audio_conversion": sum(
            1 for path_analyses in by_path.values()
            if any(any(problem.get("component") == "audio" and problem.get("status") == "UNSUPPORTED" for problem in item.get("problems", [])) for item in path_analyses)
        ),
        "requiring_video_conversion": sum(
            1 for path_analyses in by_path.values()
            if any(any(problem.get("component") == "video" and problem.get("status") == "UNSUPPORTED" for problem in item.get("problems", [])) for item in path_analyses)
        ),
        "unknown_result": sum(
            1 for path_analyses in by_path.values()
            if any(item.get("result") == "UNKNOWN" for item in path_analyses)
        ),
        "failed_files": sum(1 for item in media_items if item.get("status") == "ERROR"),
        "ffprobe_errors": len(errors),
    }
    return {
        "summary": summary,
        "files": media_items,
        "analyses": analyses,
        "errors": errors,
    }


def terminal_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "Jellyfin Media Compatibility Checker",
        "",
        "Summary:",
        f"  Scanned files: {summary.get('scanned_files', 0)}",
        f"  Direct Play for all profiles: {summary.get('supported_by_all_profiles', 0)}",
        f"  Requiring remux: {summary.get('requiring_remux', 0)}",
        f"  Requiring audio conversion: {summary.get('requiring_audio_conversion', 0)}",
        f"  Requiring video conversion: {summary.get('requiring_video_conversion', 0)}",
        f"  Unknown result: {summary.get('unknown_result', 0)}",
        f"  Files with FFprobe errors: {summary.get('failed_files', 0)}",
        "",
    ]
    reported_error_paths = set()
    for media in report.get("files", []):
        if media.get("status") != "ERROR":
            continue
        path = media.get("path", "<unknown>")
        reported_error_paths.add(path)
        lines.extend([
            f"Movie: {path}",
            "  Result: ERROR",
            f"  FFprobe error: {media.get('error', '<unknown error>')}",
            "",
        ])
    for analysis in report.get("analyses", []):
        media = analysis.get("media") or {}
        lines.extend([
            f"Movie: {media.get('path', '<unknown>')}",
            f"  Container: {(media.get('container') or {}).get('format_name', '<unknown>')}",
            "  Video: " + ", ".join(str(item.get("codec_name")) for item in media.get("video", [])),
            "  Audio: " + ", ".join(str(item.get("codec_name")) for item in media.get("audio", [])),
            "  Subtitles: " + ", ".join(str(item.get("codec_name")) for item in media.get("subtitles", [])),
            f"  {analysis.get('profile_name', analysis.get('profile_id'))}: {analysis.get('result')}",
            f"    Selected tracks: {analysis.get('selected_tracks')}",
        ])
        for problem in analysis.get("problems", []):
            lines.append(f"    Problem: {problem.get('message')}")
        for recommendation in analysis.get("recommendations", []):
            if recommendation.get("command"):
                lines.append(f"    Recommendation: {recommendation['command']}")
        lines.append("")
    for error in report.get("errors", []):
        if error.get("path") in reported_error_paths:
            continue
        lines.append(f"Error: {error.get('path')}: {error.get('error')}")
    return "\n".join(lines)


def json_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def csv_report(report: dict[str, Any]) -> str:
    output = io.StringIO()
    fieldnames = [
        "path",
        "profile_id",
        "profile_name",
        "result",
        "container",
        "video_codecs",
        "audio_codecs",
        "subtitle_codecs",
        "selected_video",
        "selected_audio",
        "selected_subtitle",
        "problems",
        "recommendations",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for media in report.get("files", []):
        if media.get("status") != "ERROR":
            continue
        writer.writerow({
            "path": media.get("path", ""),
            "result": "ERROR",
            "problems": media.get("error", ""),
        })
    for analysis in report.get("analyses", []):
        media = analysis.get("media") or {}
        writer.writerow({
            "path": media.get("path", ""),
            "profile_id": analysis.get("profile_id", ""),
            "profile_name": analysis.get("profile_name", ""),
            "result": analysis.get("result", ""),
            "container": (media.get("container") or {}).get("format_name", ""),
            "video_codecs": ",".join(str(item.get("codec_name", "")) for item in media.get("video", [])),
            "audio_codecs": ",".join(str(item.get("codec_name", "")) for item in media.get("audio", [])),
            "subtitle_codecs": ",".join(str(item.get("codec_name", "")) for item in media.get("subtitles", [])),
            "selected_video": (analysis.get("selected_tracks") or {}).get("video", ""),
            "selected_audio": (analysis.get("selected_tracks") or {}).get("audio", ""),
            "selected_subtitle": (analysis.get("selected_tracks") or {}).get("subtitle", ""),
            "problems": _problems_text(analysis.get("problems", [])),
            "recommendations": " | ".join(item.get("command", "") for item in analysis.get("recommendations", [])),
        })
    return output.getvalue()

