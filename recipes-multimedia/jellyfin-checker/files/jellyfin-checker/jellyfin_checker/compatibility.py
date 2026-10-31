"""Profile-based media compatibility evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .profile_manager import status_from_rule


DIRECT_PLAY = "DIRECT_PLAY"
DIRECT_STREAM = "DIRECT_STREAM"
TRANSCODING = "TRANSCODING"
CONDITIONAL = "CONDITIONAL"
UNKNOWN = "UNKNOWN"


@dataclass
class Problem:
    component: str
    parameter: str
    actual: Any
    expected: Any
    status: str
    impact: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "parameter": self.parameter,
            "actual": self.actual,
            "expected": self.expected,
            "status": self.status,
            "impact": self.impact,
            "message": self.message,
        }


def _normalise(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def normalise_codec(codec: Any, component: str) -> str:
    value = _normalise(codec)
    aliases = {
        "avc": "h264",
        "avc1": "h264",
        "avc3": "h264",
        "h265": "hevc",
        "x265": "hevc",
        "mpeg4": "mpeg4",
        "vp09": "vp9",
        "av01": "av1",
        "mp4a": "aac",
        "eac3": "eac3",
        "ac3": "ac3",
        "dca": "dts",
        "subrip": "srt",
        "ass": "ass",
        "ssa": "ass",
        "hdmpgssubtitle": "pgssub",
        "hdmvpgssubtitle": "pgssub",
        "hdmipgssub": "pgssub",
        "webvtt": "webvtt",
    }
    value = aliases.get(value, value)
    if component == "subtitle" and value == "text":
        return "unknown"
    return value


def normalise_container(format_name: Any) -> str:
    raw_value = str(format_name or "").strip().lower()
    if raw_value.startswith("mov,mp4,m4a,3gp,3g2,mj2"):
        return "mp4"
    value = raw_value.split(",")[0]
    return {
        "matroska": "mkv",
        "mpegts": "ts",
        "mpeg": "mpegts",
        "webm": "webm",
    }.get(value, value)


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _level_text(value: Any) -> str | None:
    number = _as_number(value)
    if number is None:
        return None if value is None else str(value)
    if number >= 10 and number.is_integer():
        return f"{number / 10:.1f}"
    return f"{number:.1f}" if not number.is_integer() else str(int(number))


def _bit_depth(stream: dict[str, Any]) -> int | None:
    value = _as_number(stream.get("bits_per_raw_sample"))
    if value:
        return int(value)
    pixel_format = str(stream.get("pix_fmt") or "")
    match = re.search(r"p(10|12|14|16)(?:le|be)?", pixel_format)
    if match:
        return int(match.group(1))
    if pixel_format:
        return 8
    return None


def _frame_rate(stream: dict[str, Any]) -> float | None:
    value = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if not value or value == "0/0":
        return None
    try:
        return float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError):
        return _as_number(value)


def _impact(component: str, status: str) -> str:
    if status == "CONDITIONAL":
        return CONDITIONAL
    if status == "UNKNOWN":
        return UNKNOWN
    if component == "video":
        return TRANSCODING
    return DIRECT_STREAM


def _problem(
    problems: list[Problem],
    component: str,
    parameter: str,
    actual: Any,
    expected: Any,
    status: str,
    message: str,
) -> None:
    status = status.upper()
    if status == "SUPPORTED":
        return
    problems.append(Problem(
        component=component,
        parameter=parameter,
        actual=actual,
        expected=expected,
        status=status,
        impact=_impact(component, status),
        message=message,
    ))


def _rule_for(profile: dict[str, Any], section: str, codec: str) -> dict[str, Any] | None:
    section_data = profile.get(section) or {}
    rule = section_data.get(codec)
    return rule if isinstance(rule, dict) else None


def _check_codec(
    problems: list[Problem],
    component: str,
    codec: str,
    rule: dict[str, Any] | None,
) -> None:
    if rule is None:
        _problem(
            problems,
            component,
            "codec_name",
            codec,
            "a rule with a verified status",
            UNKNOWN,
            f"{component.title()} codec {codec or '<missing>'} has no verified profile rule.",
        )
        return
    status = status_from_rule(rule)
    if status != "SUPPORTED":
        _problem(
            problems,
            component,
            "codec_name",
            codec,
            status,
            status,
            f"{component.title()} codec {codec or '<missing>'} is {status.lower()} for this profile.",
        )


def _constraint(
    problems: list[Problem],
    component: str,
    parameter: str,
    actual: Any,
    allowed: Any,
    message: str,
) -> None:
    if allowed is None:
        return
    allowed_values = allowed if isinstance(allowed, list) else [allowed]
    if actual is None:
        _problem(problems, component, parameter, actual, allowed, UNKNOWN, f"Cannot verify {parameter}: FFprobe did not report a value.")
        return
    actual_normalised = _normalise(actual)
    if not any(actual_normalised == _normalise(item) for item in allowed_values):
        _problem(problems, component, parameter, actual, allowed, "UNSUPPORTED", message)


def _check_video(problems: list[Problem], stream: dict[str, Any], profile: dict[str, Any]) -> None:
    codec = normalise_codec(stream.get("codec_name"), "video")
    rule = _rule_for(profile, "video", codec)
    _check_codec(problems, "video", codec, rule)
    if not rule or status_from_rule(rule) == "UNSUPPORTED":
        return

    profiles = rule.get("profiles")
    if profiles:
        _constraint(problems, "video", "profile", stream.get("profile"), profiles, f"Video profile {stream.get('profile')} is not in the verified profile set.")

    levels = rule.get("levels")
    if levels and stream.get("level") is not None:
        actual_level = _level_text(stream.get("level"))
        allowed_levels = [_level_text(level) for level in levels]
        if actual_level not in allowed_levels:
            _problem(problems, "video", "level", actual_level, levels, "UNSUPPORTED", f"Video level {actual_level} is not supported by this profile.")

    _constraint(problems, "video", "bit_depth", _bit_depth(stream), rule.get("bit_depth"), f"Video bit depth {_bit_depth(stream)} is outside the verified profile limits.")
    _constraint(problems, "video", "pix_fmt", stream.get("pix_fmt"), rule.get("pixel_formats"), f"Pixel format {stream.get('pix_fmt')} is outside the verified profile limits.")

    max_width = rule.get("max_width")
    max_height = rule.get("max_height")
    width = _as_number(stream.get("width"))
    height = _as_number(stream.get("height"))
    if max_width is not None and (width is None or width > float(max_width)):
        _problem(problems, "video", "width", stream.get("width"), f"<= {max_width}", "UNSUPPORTED", f"Video width {stream.get('width')} exceeds {max_width}.")
    if max_height is not None and (height is None or height > float(max_height)):
        _problem(problems, "video", "height", stream.get("height"), f"<= {max_height}", "UNSUPPORTED", f"Video height {stream.get('height')} exceeds {max_height}.")

    frame_rate = _frame_rate(stream)
    maximum_rate = _as_number(rule.get("max_framerate"))
    if maximum_rate is not None and (frame_rate is None or frame_rate > maximum_rate + 0.001):
        _problem(problems, "video", "framerate", frame_rate, f"<= {maximum_rate}", "UNSUPPORTED", f"Framerate {frame_rate} exceeds {maximum_rate}.")

    _constraint(problems, "video", "sample_aspect_ratio", stream.get("sample_aspect_ratio"), rule.get("sample_aspect_ratios"), "Sample aspect ratio is not supported by this profile.")
    _constraint(problems, "video", "display_aspect_ratio", stream.get("display_aspect_ratio"), rule.get("display_aspect_ratios"), "Display aspect ratio is not supported by this profile.")

    hdr = stream.get("hdr") or {}
    if hdr.get("is_hdr"):
        hdr_rules = profile.get("hdr") or {}
        hdr_type = hdr.get("type") or "unknown"
        hdr_rule = hdr_rules.get(hdr_type)
        if not isinstance(hdr_rule, dict):
            _problem(problems, "video", "hdr", hdr_type, "a verified HDR rule", UNKNOWN, f"HDR type {hdr_type} has no verified profile rule.")
        else:
            status = status_from_rule(hdr_rule)
            _problem(problems, "video", "hdr", hdr_type, status, status, f"HDR type {hdr_type} is {status.lower()} for this profile.")


def _check_audio(problems: list[Problem], stream: dict[str, Any], profile: dict[str, Any]) -> None:
    codec = normalise_codec(stream.get("codec_name"), "audio")
    rule = _rule_for(profile, "audio", codec)
    _check_codec(problems, "audio", codec, rule)
    if not rule:
        return
    max_channels = rule.get("max_channels")
    channels = _as_number(stream.get("channels"))
    if max_channels is not None and (channels is None or channels > float(max_channels)):
        _problem(problems, "audio", "channels", stream.get("channels"), f"<= {max_channels}", "UNSUPPORTED", f"Audio channel count {stream.get('channels')} exceeds {max_channels}.")
    _constraint(problems, "audio", "channel_layout", stream.get("channel_layout"), rule.get("channel_layouts"), "Audio channel layout is not supported by this profile.")


def _check_subtitle(problems: list[Problem], stream: dict[str, Any], profile: dict[str, Any], container: str) -> None:
    codec = normalise_codec(stream.get("codec_name"), "subtitle")
    rule = _rule_for(profile, "subtitles", codec)
    _check_codec(problems, "subtitle", codec, rule)
    if not rule:
        return
    container_rules = rule.get("containers")
    if isinstance(container_rules, dict):
        container_rule = container_rules.get(container)
        status = status_from_rule(container_rule)
        _problem(problems, "subtitle", "container", container, status, status, f"Subtitle codec {codec} is {status.lower()} in {container}.")


def _check_container(problems: list[Problem], media: dict[str, Any], profile: dict[str, Any]) -> str:
    container = normalise_container((media.get("container") or {}).get("format_name"))
    rule = (profile.get("containers") or {}).get(container)
    status = status_from_rule(rule)
    _problem(problems, "container", "format_name", container, status, status, f"Container {container or '<missing>'} is {status.lower()} for this profile.")
    return container


def _evaluate_selection(
    media: dict[str, Any],
    profile: dict[str, Any],
    video_index: int | None,
    audio_index: int | None,
    subtitle_index: int | None,
) -> dict[str, Any]:
    problems: list[Problem] = []
    container = _check_container(problems, media, profile)
    videos = media.get("video") or []
    audios = media.get("audio") or []
    subtitles = media.get("subtitles") or []
    video_position = 0 if video_index is None else video_index
    video = videos[video_position] if videos and 0 <= video_position < len(videos) else None
    audio = audios[audio_index] if audio_index is not None and 0 <= audio_index < len(audios) else None
    subtitle = subtitles[subtitle_index] if subtitle_index is not None and 0 <= subtitle_index < len(subtitles) else None

    if video is None:
        _problem(problems, "video", "stream", None, "at least one video stream", UNKNOWN, "No selectable video stream was reported by FFprobe.")
    else:
        _check_video(problems, video, profile)
    if audio is not None:
        _check_audio(problems, audio, profile)
    if subtitle is not None:
        _check_subtitle(problems, subtitle, profile, container)

    impacts = {problem.impact for problem in problems}
    if TRANSCODING in impacts:
        result = TRANSCODING
    elif DIRECT_STREAM in impacts:
        result = DIRECT_STREAM
    elif UNKNOWN in impacts:
        result = UNKNOWN
    elif CONDITIONAL in impacts:
        result = CONDITIONAL
    else:
        result = DIRECT_PLAY
    return {
        "result": result,
        "selected_tracks": {
            "video": video.get("index") if video else None,
            "audio": audio.get("index") if audio else None,
            "subtitle": subtitle.get("index") if subtitle else None,
        },
        "problems": [problem.as_dict() for problem in problems],
    }


def _score(result: dict[str, Any]) -> tuple[int, int]:
    # Prefer a known conditional path over a known path that needs an extra
    # conversion. This is important when an alternative audio track avoids a
    # codec problem while the container still needs a remux.
    ranks = {DIRECT_PLAY: 5, CONDITIONAL: 4, DIRECT_STREAM: 3, UNKNOWN: 2, TRANSCODING: 1}
    return ranks.get(result["result"], 0), -len(result.get("problems", []))


def evaluate_media(
    media: dict[str, Any],
    profile: dict[str, Any],
    *,
    video_index: int | None = None,
    audio_index: int | None = None,
    subtitle_index: int | None = None,
    no_subtitles: bool = False,
) -> dict[str, Any]:
    """Evaluate the best available audio/subtitle selection for a profile."""

    videos = media.get("video") or []
    audios = media.get("audio") or []
    subtitles = media.get("subtitles") or []
    video_index = 0 if video_index is None and videos else video_index
    audio_choices = [audio_index] if audio_index is not None else ([item for item in range(len(audios))] or [None])
    if subtitle_index is not None:
        subtitle_choices = [subtitle_index]
    elif no_subtitles:
        subtitle_choices = [None]
    else:
        subtitle_choices = [None, *range(len(subtitles))]

    candidates = [
        _evaluate_selection(media, profile, video_index, selected_audio, selected_subtitle)
        for selected_audio in audio_choices
        for selected_subtitle in subtitle_choices
    ]
    selected = max(candidates, key=_score)
    alternatives = [
        {
            "selected_tracks": item["selected_tracks"],
            "result": item["result"],
            "problem_count": len(item["problems"]),
        }
        for item in candidates
        if item is not selected
    ]

    audio_options = []
    for index, audio in enumerate(audios):
        option = _evaluate_selection(media, profile, video_index, index, None)
        audio_options.append({
            "index": audio.get("index", index),
            "codec_name": audio.get("codec_name"),
            "language": audio.get("language"),
            "title": audio.get("title"),
            "result_without_subtitles": option["result"],
        })
    subtitle_options = []
    selected_audio_id = selected["selected_tracks"].get("audio")
    selected_audio_position = next(
        (position for position, audio in enumerate(audios) if audio.get("index") == selected_audio_id),
        None,
    )
    for index, subtitle in enumerate(subtitles):
        option = _evaluate_selection(media, profile, video_index, selected_audio_position, index)
        subtitle_options.append({
            "index": subtitle.get("index", index),
            "codec_name": subtitle.get("codec_name"),
            "language": subtitle.get("language"),
            "title": subtitle.get("title"),
            "result_with_selected_audio": option["result"],
        })

    return {
        "profile_id": profile.get("id"),
        "profile_name": profile.get("name", profile.get("id")),
        "result": selected["result"],
        "selected_tracks": selected["selected_tracks"],
        "problems": selected["problems"],
        "alternatives": alternatives,
        "audio_options": audio_options,
        "subtitle_options": subtitle_options,
    }

