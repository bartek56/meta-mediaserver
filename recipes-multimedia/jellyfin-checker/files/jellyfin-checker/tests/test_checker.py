import json
from pathlib import Path

from jellyfin_checker.compatibility import DIRECT_PLAY, DIRECT_STREAM, evaluate_media
from jellyfin_checker.conversion_advisor import recommendations_for
from jellyfin_checker.ffprobe import parse_ffprobe
from jellyfin_checker.profile_manager import ProfileManager
from jellyfin_checker.report import csv_report, make_report, terminal_report


FIXTURE = Path(__file__).with_name("ffprobe-movie.json")


def profiles():
    manager = ProfileManager()
    return manager.load("firefox_linux"), manager.load("chrome_linux")


def media_fixture():
    return parse_ffprobe(json.loads(FIXTURE.read_text()), "/media/example.mkv")


def test_ffprobe_parser_keeps_all_streams_and_metadata():
    media = media_fixture()
    assert len(media["video"]) == 1
    assert len(media["audio"]) == 2
    assert len(media["subtitles"]) == 1
    assert media["audio"][0]["language"] == "eng"
    assert media["subtitles"][0]["disposition"]["default"] == 1
    assert media["container"]["format_name"] == "matroska,webm"


def test_unsupported_audio_does_not_hide_compatible_alternative():
    media = media_fixture()
    media["container"]["format_name"] = "mov,mp4,m4a,3gp,3g2,mj2"
    _, chrome = profiles()
    result = evaluate_media(media, chrome)
    assert result["result"] == DIRECT_PLAY
    assert result["selected_tracks"]["audio"] == 2
    assert any(option["codec_name"] == "dts" for option in result["audio_options"])


def test_firefox_mkv_is_direct_stream_and_recommendation_is_not_executed():
    media = media_fixture()
    firefox, _ = profiles()
    result = evaluate_media(media, firefox, audio_index=1, no_subtitles=True)
    assert result["result"] == DIRECT_STREAM
    recommendations = recommendations_for(media, result)
    assert recommendations
    assert "-c:v copy" in recommendations[0]["command"]
    assert "-c:s mov_text" in recommendations[0]["command"]
    assert "-map 0 -c copy" not in recommendations[0]["command"]


def test_device_profile_inherits_and_overrides(tmp_path):
    device_dir = tmp_path / "profiles" / "devices"
    device_dir.mkdir(parents=True)
    (device_dir / "test_device.json").write_text(
        json.dumps({
            "id": "test_device",
            "name": "Test device",
            "type": "device",
            "inherits": "chrome_linux",
            "manual_overrides": {"audio": {"dts": {"status": "SUPPORTED", "manual": True}}},
        }),
        encoding="utf-8",
    )
    manager = ProfileManager(config_dir=tmp_path)
    profile = manager.load("test_device")
    assert profile["video"]["h264"]["status"] == "SUPPORTED"
    assert profile["audio"]["dts"]["status"] == "SUPPORTED"


def test_ffprobe_error_is_reported_as_a_movie_without_stopping_scan():
    path = "/media/Joker (2019) [BluRay]/Joker.mp4"
    error = "FFprobe failed: moov atom not found"
    report = make_report(
        [{"path": path, "status": "ERROR", "error": error}],
        [],
        [{"path": path, "error": error}],
    )

    assert report["summary"]["scanned_files"] == 1
    assert report["summary"]["failed_files"] == 1
    output = terminal_report(report)
    assert f"Movie: {path}" in output
    assert "Result: ERROR" in output
    assert error in output
    assert output.count(error) == 1
    assert "ERROR" in csv_report(report)

