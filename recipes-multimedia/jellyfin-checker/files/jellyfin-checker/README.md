# Jellyfin Media Compatibility Checker

`jellyfin-checker` scans media files with `ffprobe` and compares the reported
streams with explicit, source-labelled client profiles. It never modifies a
media file, starts FFmpeg, or requires a Jellyfin server/API.

## Usage

```text
jellyfin-checker scan /mnt/media
jellyfin-checker scan /mnt/media --profiles firefox_linux,chrome_linux --format csv
jellyfin-checker inspect movie.mkv --format json
jellyfin-checker profiles list
jellyfin-checker profiles update
jellyfin-checker profiles edit firefox_linux
```

The default profile data is intentionally conservative. `CONDITIONAL` and
`UNKNOWN` mean that the result must be verified on the target device. Profile
updates only snapshot the documented source and report its checksum; they do
not parse HTML or overwrite rules and manual edits.

Audio and subtitle alternatives are considered automatically. Use
`--audio-index`, `--subtitle-index`, or `--no-subtitles` to force a selection.
Recommendations can be saved with `--recommendations report.txt`; generated
FFmpeg commands are suggestions and are never executed.

If FFprobe cannot read a file, the file is reported as `ERROR` with the full
FFprobe message and scanning continues with the next movie.

The supported extensions are MKV, MP4, AVI, MOV, M4V, TS, M2TS and WEBM.
