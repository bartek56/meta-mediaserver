"""CLI for scanning media and managing compatibility profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .compatibility import evaluate_media
from .conversion_advisor import add_recommendations, write_recommendations
from .ffprobe import FFProbeError, probe_file
from .profile_manager import ProfileManager
from .report import csv_report, json_report, make_report, terminal_report
from .scanner import iter_media_files


def _profile_ids(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "firefox_linux,chrome_linux").split(",") if item.strip()]


def _analysis_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profiles", default="firefox_linux,chrome_linux", help="Comma-separated profile IDs")
    parser.add_argument("--format", choices=("terminal", "json", "csv"), default="terminal")
    parser.add_argument("--output", help="Write the selected report format to this file")
    parser.add_argument("--recommendations", help="Write FFmpeg recommendations to a TXT file")
    parser.add_argument("--ffprobe", default="ffprobe", help="FFprobe executable")
    parser.add_argument("--video-index", type=int, help="Video stream list index (default: first)")
    parser.add_argument("--audio-index", type=int, help="Audio stream list index; default chooses the best alternative")
    parser.add_argument("--subtitle-index", type=int, help="Subtitle stream list index")
    parser.add_argument("--no-subtitles", action="store_true", help="Do not select a subtitle stream")
    parser.add_argument("--profiles-dir", help="User profile/configuration directory")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jellyfin-checker", description="Check media compatibility with Jellyfin client profiles")
    commands = parser.add_subparsers(dest="command", required=True)

    scan_parser = commands.add_parser("scan", help="Recursively scan a directory or inspect one supported file")
    scan_parser.add_argument("path")
    _analysis_options(scan_parser)

    inspect_parser = commands.add_parser("inspect", help="Inspect one media file")
    inspect_parser.add_argument("path")
    _analysis_options(inspect_parser)

    profile_parser = commands.add_parser("profiles", help="List, update or edit profiles")
    profile_commands = profile_parser.add_subparsers(dest="profiles_command", required=True)
    list_parser = profile_commands.add_parser("list", help="List available profiles")
    list_parser.add_argument("--profiles-dir")
    update_parser = profile_commands.add_parser("update", help="Snapshot official sources and report changes")
    update_parser.add_argument("--profile", action="append", dest="profiles")
    update_parser.add_argument("--profiles-dir")
    edit_parser = profile_commands.add_parser("edit", help="Create a user copy and open it in EDITOR")
    edit_parser.add_argument("profile_id")
    edit_parser.add_argument("--profiles-dir")
    return parser


def _manager(args: argparse.Namespace) -> ProfileManager:
    return ProfileManager(config_dir=getattr(args, "profiles_dir", None))


def _render(report: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json_report(report)
    if output_format == "csv":
        return csv_report(report)
    return terminal_report(report) + "\n"


def _run_scan(args: argparse.Namespace) -> int:
    manager = _manager(args)
    profiles = []
    for profile_id in _profile_ids(args.profiles):
        try:
            profiles.append(manager.load(profile_id))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"Cannot load profile {profile_id}: {exc}") from exc

    media_items: list[dict[str, Any]] = []
    analyses: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    try:
        if args.command == "inspect":
            inspect_path = Path(args.path)
            if not inspect_path.is_file():
                raise FileNotFoundError(inspect_path)
            paths = iter((inspect_path,))
        else:
            paths = iter_media_files(args.path)
    except FileNotFoundError as exc:
        raise SystemExit(f"Path does not exist: {exc}") from exc

    for media_path in paths:
        try:
            media = probe_file(media_path, ffprobe_bin=args.ffprobe)
        except FFProbeError as exc:
            error = {"path": str(media_path), "error": str(exc)}
            errors.append(error)
            # Keep the failed file in the report as a movie entry.  The
            # scanner deliberately continues with the next file.
            media_items.append({
                "path": str(media_path),
                "status": "ERROR",
                "error": str(exc),
            })
            continue
        media_items.append(media)
        for profile in profiles:
            analysis = evaluate_media(
                media,
                profile,
                video_index=args.video_index,
                audio_index=args.audio_index,
                subtitle_index=args.subtitle_index,
                no_subtitles=args.no_subtitles,
            )
            analysis = add_recommendations(media, analysis)
            analyses.append({"media": media, **analysis})

    report = make_report(media_items, analyses, errors)
    rendered = _render(report, args.format)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.recommendations:
        write_recommendations(analyses, args.recommendations)
    return 0


def _run_profiles(args: argparse.Namespace) -> int:
    manager = _manager(args)
    if args.profiles_command == "list":
        for profile in manager.list_profiles():
            print(f"{profile['id']}\t{profile['type']}\t{profile['name']}")
        return 0
    if args.profiles_command == "edit":
        try:
            path = manager.edit(args.profile_id)
        except (OSError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        print(path)
        return 0
    try:
        changes = manager.update_official(args.profiles)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(changes, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"scan", "inspect"}:
        if args.command == "inspect":
            args.path = str(Path(args.path))
        return _run_scan(args)
    return _run_profiles(args)

