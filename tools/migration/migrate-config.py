#!/usr/bin/env python3
"""Safe, host-side configuration inventory and migration over SSH."""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import html
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MANIFEST = Path(__file__).with_name("migration-files.txt")
DEFAULT_REPORT_ROOT = Path(__file__).resolve().parent / "reports"
VERSION_FILES = (
    "/etc/mediaserver/build-info",
    "/etc/mediaserver/build-layers",
)
MIGRATION_SERVICES = (
    "mpd", "snapserver", "snapclient", "minidlna", "pulseaudio",
    "transmission-daemon", "smbd", "jellyfin",
)
FIELDS = ("path", "type", "mode", "uid", "gid", "size", "atime_ns", "mtime_ns", "sha256", "link_target", "class", "decision")
VERBOSE = True


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def log(message: str) -> None:
    if VERBOSE:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {message}", file=sys.stderr, flush=True)


def safe_path(path: str) -> bool:
    return path.startswith("/") and "\n" not in path and "\r" not in path and ".." not in Path(path).parts


def read_manifest(path: Path) -> list[tuple[str, str]]:
    entries = []
    with path.open() as stream:
        for number, line in enumerate(stream, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split(None, 1)
            if len(fields) != 2 or fields[0] not in {"A", "A!", "B", "C", "D"} or not safe_path(fields[1]):
                fail(f"invalid manifest entry {path}:{number}; expected '<class> <absolute-path>' (classes: A, A!, B, C, D)")
            entries.append((fields[1], fields[0]))
    if not entries:
        fail(f"migration manifest is empty: {path}")
    return entries


def classify(path: str, manifest: dict[str, str]) -> tuple[str, str, str]:
    if path not in manifest:
        fail(f"path is missing from migration manifest: {path}")
    cls = manifest[path]
    description_class = "A" if cls == "A!" else cls
    descriptions = {
        "A": "safe service configuration",
        "B": "requires manual verification",
        "C": "network, access, or device identity",
        "D": "secret, runtime, or application data",
    }
    decisions = {
        "A": "compare target and apply approved changes",
        "B": "manual review",
        "C": "do not overwrite automatically",
        "D": "do not migrate automatically",
    }
    return cls, descriptions[description_class], decisions[description_class]


def ssh_command(host: str, user: str, port: int, identity: str, command: str,
                data: bytes | None = None, output_file: Path | None = None,
                input_file: Path | None = None) -> bytes:
    destination = f"{user}@{host}" if user else host
    args = ["ssh", "-o", "RequestTTY=no", "-o", "ClearAllForwardings=yes", "-p", str(port)]
    if identity:
        args += ["-i", identity]
    args += ["--", destination, command]
    #log(f"SSH start: {destination}  command={command!r}")
    if data is not None and input_file is not None:
        raise ValueError("ssh_command accepts either data or input_file, not both")
    if data is not None:
        log(f"SSH stdin: {len(data)} bytes")
    elif input_file is not None:
        log(f"SSH stdin file: {input_file} ({input_file.stat().st_size} bytes)")
    started = time.monotonic()
    with tempfile.TemporaryFile() as error_stream:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if data is not None or input_file is not None else None,
            stdout=subprocess.PIPE,
            stderr=error_stream,
        )
        if data is not None and process.stdin is not None:
            process.stdin.write(data)
            process.stdin.close()
        elif input_file is not None and process.stdin is not None:
            with input_file.open("rb") as source_stream:
                for chunk in iter(lambda: source_stream.read(1024 * 1024), b""):
                    process.stdin.write(chunk)
            process.stdin.close()
        output_parts = []
        output_size = 0
        last_report = time.monotonic()
        destination_stream = output_file.open("wb") if output_file else None
        try:
            while process.stdout is not None:
                chunk = process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                if destination_stream:
                    destination_stream.write(chunk)
                else:
                    output_parts.append(chunk)
                output_size += len(chunk)
                if time.monotonic() - last_report >= 1:
                    log(f"SSH progress: {destination} stdout={output_size} bytes")
                    last_report = time.monotonic()
        finally:
            if destination_stream:
                destination_stream.close()
        process.wait()
        error_stream.seek(0)
        stderr = error_stream.read()
    stdout = b"".join(output_parts)
    elapsed = time.monotonic() - started
    log(f"SSH end: {destination}  exit={process.returncode} stdout={output_size} bytes elapsed={elapsed:.1f}s")
    if process.returncode:
        raise RuntimeError(f"SSH command failed on {destination}: {stderr.decode(errors='replace').strip()}")
    return stdout


def read_version(args: argparse.Namespace, side: str, version_file: str) -> bytes:
    if side == "source":
        host, user, port, identity, root = args.source_host, args.source_user, args.source_port, args.source_identity, args.source_root
    else:
        host, user, port, identity, root = args.target_host, args.target_user, args.target_port, args.target_identity, args.target_root
    if host:
        return ssh_command(host, user, port, identity, f"cat -- {shlex.quote(version_file)}")
    path = root / version_file.lstrip("/")
    if side == "target":
        result = subprocess.run(["sudo", "cat", "--", str(path)], stdout=subprocess.PIPE,
                                check=False)
        if result.returncode:
            raise OSError(f"sudo cat failed: {path}")
        return result.stdout
    return path.read_bytes()


def save_versions(args: argparse.Namespace, report: Path) -> None:
    records = []
    for side in ("source", "target"):
        for version_file in VERSION_FILES:
            try:
                data = read_version(args, side, version_file)
            except (OSError, RuntimeError) as error:
                fail(f"{side} has no valid {version_file}: {error}")
            suffix = Path(version_file).name
            path = report / f"{side}-{suffix}"
            path.write_bytes(data)
            identity = hashlib.sha256(data).hexdigest()
            records.append((side, version_file, identity, path.name))
            log(f"{side}: {version_file} saved ({identity})")
    with (report / "version-comparison.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("side", "path", "sha256", "snapshot"))
        writer.writerows(records)


def expanded_manifest(root: Path, manifest: list[tuple[str, str]]) -> list[tuple[str, str]]:
    expanded = []
    known = {path for path, _ in expanded}
    for path, cls in manifest:
        candidate = root / path.lstrip("/")
        if cls == "A!" and candidate.is_symlink():
            normalized = path.rstrip("/")
            if normalized not in known:
                expanded.append((normalized, cls)); known.add(normalized)
            try:
                link_target = Path(os.readlink(candidate))
                resolved_candidate = (root / str(link_target).lstrip("/")
                                      if link_target.is_absolute()
                                      else candidate.parent / link_target)
                resolved = resolved_candidate.resolve(strict=True)
                resolved_relative = "/" + str(resolved.relative_to(root)).replace(os.sep, "/")
                if resolved.is_dir() and safe_path(resolved_relative) and resolved_relative not in known:
                    expanded.append((resolved_relative, cls)); known.add(resolved_relative)
                    log(f"{root}: resolved opaque directory link {normalized} -> {resolved_relative}")
            except (OSError, ValueError):
                log(f"{root}: opaque directory link target is unavailable: {normalized}")
            continue
        if cls == "A!" and candidate.is_dir() and not candidate.is_symlink():
            normalized = path.rstrip("/")
            if normalized not in known:
                expanded.append((normalized, cls)); known.add(normalized)
            log(f"{root}: keeping opaque directory as one manifest entry {normalized}")
            continue
        if candidate.is_dir() and not candidate.is_symlink() and cls != "A!":
            skip_hidden = path.rstrip("/") == "/home"
            for directory, directories, files in os.walk(candidate, followlinks=False):
                directories[:] = [name for name in directories
                                  if not (Path(directory) / name).is_symlink()
                                  and not (skip_hidden and name.startswith("."))]
                if skip_hidden:
                    files[:] = [name for name in files if not name.startswith(".")]
                for name in files:
                    child = Path(directory) / name
                    relative = "/" + str(child.relative_to(root)).replace(os.sep, "/")
                    if safe_path(relative) and relative not in known:
                        expanded.append((relative, cls)); known.add(relative)
                for name in directories:
                    child = Path(directory) / name
                    if child.is_symlink():
                        relative = "/" + str(child.relative_to(root)).replace(os.sep, "/")
                        if safe_path(relative) and relative not in known:
                            expanded.append((relative, cls)); known.add(relative)
                        try:
                            resolved = child.resolve(strict=True)
                            resolved_relative = "/" + str(resolved.relative_to(root)).replace(os.sep, "/")
                            if resolved.is_file() and safe_path(resolved_relative) and resolved_relative not in known:
                                expanded.append((resolved_relative, cls)); known.add(resolved_relative)
                        except (OSError, ValueError):
                            pass
            log(f"{root}: expanded manifest directory {path}")
            continue
        if candidate.exists() or candidate.is_symlink():
            if path not in known:
                expanded.append((path, cls)); known.add(path)
        if not candidate.is_symlink():
            continue
        try:
            link_target = Path(os.readlink(candidate))
            resolved_candidate = root / str(link_target).lstrip("/") if link_target.is_absolute() else candidate.parent / link_target
            resolved = resolved_candidate.resolve(strict=True)
            relative = "/" + str(resolved.relative_to(root)).replace(os.sep, "/")
        except (OSError, ValueError):
            continue
        if resolved.is_file() and safe_path(relative) and relative not in known:
            expanded.append((relative, cls))
            known.add(relative)
            log(f"{root}: resolved manifest link {path} -> {relative}")
    return expanded


def path_list(root: Path, manifest: list[tuple[str, str]]) -> list[Path]:
    found: list[Path] = []
    for item, cls in manifest:
        current = root / item.lstrip("/")
        if cls == "A!" and current.is_dir() and not current.is_symlink():
            found.append(current)
        elif current.is_file() or current.is_symlink():
            found.append(current)
    return found


def digest(path: Path) -> str:
    if path.is_symlink():
        return "SYMLINK:" + os.readlink(path)
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inventory(root: Path, side: str, report: Path, manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    records = []
    requested_opaque = {path.rstrip("/") for path, cls in manifest if cls == "A!"}
    manifest = expanded_manifest(root, manifest)
    opaque_present = {path for path, cls in manifest if cls == "A!"}
    for path in sorted(requested_opaque - opaque_present):
        message = ("opaque directory not found on source; check exact spelling and letter case"
                   if side == "source" else
                   "opaque directory not found on target; it can be copied by --apply")
        log(f"{side}: {path}: {message}")
    manifest_map = {path: cls for path, cls in manifest}
    output = report / f"{side}.tsv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        files = path_list(root, manifest)
        log(f"{side}: analyzing {len(files)} present files from {len(manifest)} manifest entries")
        for index, file_path in enumerate(files, 1):
            relative = "/" + str(file_path.relative_to(root)).replace(os.sep, "/")
            if not safe_path(relative):
                continue
            info = file_path.lstat()
            manifest_class = manifest_map[relative]
            kind = ("opaque directory" if manifest_class == "A!" and stat.S_ISDIR(info.st_mode)
                    else "symbolic link" if stat.S_ISLNK(info.st_mode) else "regular file")
            cls, reason, decision = classify(relative, manifest_map)
            link_target = os.readlink(file_path) if stat.S_ISLNK(info.st_mode) else ""
            try:
                file_digest = "OPAQUE" if kind == "opaque directory" else digest(file_path)
            except PermissionError as error:
                if cls in {"A", "A!"}:
                    raise PermissionError(f"cannot read class A file {file_path}; run with access to the rootfs (for example sudo): {error}") from error
                file_digest = "UNREADABLE"
                log(f"{side}: cannot read {relative}; recorded as UNREADABLE because class is {cls}")
            record = {"path": relative, "type": kind, "mode": oct(info.st_mode & 0o7777)[2:],
                      "uid": str(info.st_uid), "gid": str(info.st_gid), "size": str(info.st_size),
                      "atime_ns": str(info.st_atime_ns), "mtime_ns": str(info.st_mtime_ns),
                      "sha256": file_digest, "link_target": link_target,
                      "class": cls, "decision": f"{reason}; {decision}"}
            writer.writerow(record)
            records.append(record)
            if index % 100 == 0:
                log(f"{side}: analyzed {index}/{len(files)} entries")
        for path in sorted(requested_opaque - opaque_present):
            record = {
                "path": path, "type": "missing", "mode": "", "uid": "", "gid": "", "size": "0",
                "atime_ns": "", "mtime_ns": "", "sha256": "MISSING", "link_target": "", "class": "A!",
                "decision": ("opaque directory not found on source; check exact spelling and letter case"
                             if side == "source" else
                             "opaque directory not found on target; it can be copied by --apply"),
            }
            writer.writerow(record)
            records.append(record)
    return records


def create_analysis_archive(root: Path, records: list[dict[str, str]], report: Path, filename: str) -> Path:
    archive_path = report / filename
    with tarfile.open(archive_path, mode="w") as archive:
        for record in records:
            if record["class"] not in {"A", "A!"}:
                continue
            path = root / record["path"].lstrip("/")
            if path.exists() or path.is_symlink():
                archive.add(path, arcname=record["path"].lstrip("/"),
                            recursive=record["type"] == "opaque directory")
    log(f"analysis archive created: {archive_path} ({archive_path.stat().st_size} bytes)")
    return archive_path


def create_migration_archive(report: Path, plan: list[dict[str, str]]) -> Path:
    source_archive = report / "source-analysis.tar"
    archive_path = report / "source-migration.tar"
    planned = {item["path"].lstrip("/") for item in plan
               if item["action"] in {"copy-after-backup", "copy-new-file", "copy-symlink", "copy-opaque-directory"}}
    with tarfile.open(source_archive, mode="r") as source, tarfile.open(archive_path, mode="w") as output:
        for member in source.getmembers():
            if member.name in planned or any(member.name.startswith(path + "/") for path in planned):
                output.addfile(member, source.extractfile(member) if member.isfile() else None)
    log(f"migration archive created: {archive_path} ({archive_path.stat().st_size} bytes, files={len(planned)})")
    return archive_path


def create_opaque_package(source_archive: Path, path: str, package: Path) -> None:
    """Create one uncompressed tar for an opaque directory, retaining metadata."""
    prefix = path.lstrip("/").rstrip("/")
    with tarfile.open(source_archive, mode="r") as source, tarfile.open(package, mode="w") as output:
        selected = [member for member in source.getmembers()
                    if member.name == prefix or member.name.startswith(prefix + "/")]
        if not selected:
            raise RuntimeError(f"source migration archive has no opaque directory: {path}")
        for member in selected:
            output.addfile(member, source.extractfile(member) if member.isfile() else None)


def extract_opaque_package(package: Path, target_root: Path) -> None:
    """Safely extract a controlled opaque package, including tar metadata."""
    with tarfile.open(package, mode="r:*") as archive:
        members = archive.getmembers()
        for member in members:
            name = "/" + member.name.lstrip("/")
            if member.name.startswith("/") or not safe_path(name):
                raise RuntimeError(f"unsafe opaque archive member: {member.name}")
        archive.extractall(target_root, numeric_owner=True)


def safe_extract(data: bytes | Path, destination: Path) -> None:
    archive_size = len(data) if isinstance(data, bytes) else data.stat().st_size
    log(f"extracting remote archive: {archive_size} bytes -> {destination}")
    # ``r:*`` accepts both the uncompressed tar files created locally and
    # compressed archives from older reports.
    archive_args = {"fileobj": __import__("io").BytesIO(data)} if isinstance(data, bytes) else {"name": str(data)}
    with tarfile.open(mode="r:*", **archive_args) as archive:
        for member in archive.getmembers():
            name = "/" + member.name.lstrip("/")
            if not safe_path(name) or member.name.startswith("/"):
                raise RuntimeError(f"unsafe path in remote archive: {member.name}")
            target = destination / name.lstrip("/")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.issym() or member.islnk():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.unlink(missing_ok=True)
                target.symlink_to(member.linkname)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise RuntimeError(f"cannot read archive member: {member.name}")
                with target.open("wb") as stream:
                    shutil.copyfileobj(source, stream)


def remote_inventory(args: argparse.Namespace, side: str, report: Path, manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    host, user, port, identity = ((args.source_host, args.source_user, args.source_port, args.source_identity)
                                   if side == "source" else (args.target_host, args.target_user, args.target_port, args.target_identity))
    # BusyBox tar on the target does not provide GNU tar's -T/--null options.
    # Build an explicit, shell-quoted argument list instead. Directory entries
    # remain recursive tar inputs; no unlisted path is added.
    log(f"{side}: preparing remote inventory; {len(manifest)} explicit files")
    for index, (path, cls) in enumerate(manifest, 1):
        log(f"{side}: manifest[{index}] {cls} {path}")
    command_parts = ["set --"]
    for path, cls in manifest:
        quoted = shlex.quote(path)
        if cls == "A!":
            opaque_path = path.rstrip("/")
            opaque_quoted = shlex.quote(opaque_path)
            command_parts.append(
                f"if [ -L {opaque_quoted} ]; then set -- \"$@\" {opaque_quoted}; "
                f"resolved=$(readlink -f {opaque_quoted} 2>/dev/null || realpath {opaque_quoted} 2>/dev/null || true); "
                f"[ -d \"$resolved\" ] && set -- \"$@\" \"$resolved\"; "
                f"elif [ -d {opaque_quoted} ]; then set -- \"$@\" {opaque_quoted}; fi"
            )
            continue
        if path.rstrip("/") == "/home":
            command_parts.append(
                "for entry in $(find /home -type f ! -path '*/.*' 2>/dev/null); do "
                "set -- \"$@\" \"$entry\"; done; "
                "for entry in $(find /home -type l ! -path '*/.*' 2>/dev/null); do "
                "set -- \"$@\" \"$entry\"; "
                "link_target=$(readlink -f \"$entry\" 2>/dev/null || true); "
                "case \"$link_target\" in /*) case \"$link_target\" in */.*) ;; *) "
                "[ -f \"$link_target\" ] && set -- \"$@\" \"$link_target\" ;; esac;; esac; done"
            )
        else:
            command_parts.append(
                f"if [ -e {quoted} ] || [ -L {quoted} ]; then "
                f"set -- \"$@\" {quoted}; "
                f"if [ -L {quoted} ]; then link_target=$(readlink -f {quoted} 2>/dev/null || true); "
                f"case \"$link_target\" in /*) if [ -f \"$link_target\" ]; then set -- \"$@\" \"$link_target\"; fi;; esac; "
                f"fi; fi"
            )
        if path.endswith("/"):
            find_filter = " ! -path '*/.*'" if path.rstrip("/") == "/home" else ""
            command_parts.append(
                f"for link in $(find {quoted} -type l{find_filter} 2>/dev/null); do "
                f"resolved=$(readlink -f \"$link\" 2>/dev/null || true); "
                f"[ -f \"$resolved\" ] && set -- \"$@\" \"$link\" \"$resolved\"; done"
            )
    # Compress on the remote host before sending the archive.  This matters
    # for directory entries (for example Jellyfin), where an uncompressed tar
    # can otherwise transfer hundreds of megabytes over SSH.
    command_parts.append("exec tar -C / -cf - \"$@\"")
    command = "; ".join(command_parts)
    with tempfile.NamedTemporaryFile(prefix=f"migrate-{side}-", suffix=".tar", delete=False) as temporary:
        archive_path = Path(temporary.name)
    temporary_root = tempfile.TemporaryDirectory(prefix=f"migrate-{side}-root-")
    root = Path(temporary_root.name)
    try:
        ssh_command(host, user, port, identity, command, output_file=archive_path)
        safe_extract(archive_path, root)
        for path, cls in manifest:
            if cls != "A!":
                continue
            opaque_path = root / path.rstrip("/").lstrip("/")
            if opaque_path.is_symlink():
                try:
                    link_target = Path(os.readlink(opaque_path))
                    resolved_path = (root / str(link_target).lstrip("/")
                                     if link_target.is_absolute()
                                     else opaque_path.parent / link_target).resolve(strict=True)
                    log(f"{side}: archive contains opaque link {path} -> {resolved_path}")
                    if not resolved_path.is_dir():
                        log(f"{side}: opaque link target is not a directory in archive: {path}")
                except OSError:
                    log(f"{side}: archive contains opaque link without target: {path}")
            elif opaque_path.is_dir():
                log(f"{side}: archive contains opaque directory {path}")
            else:
                log(f"{side}: archive does not contain opaque path: {path}")
        records = inventory(root, side, report, manifest)
        create_analysis_archive(root, records, report, f"{side}-analysis.tar")
    finally:
        archive_path.unlink(missing_ok=True)
        temporary_root.cleanup()
    log(f"{side}: removed temporary extraction directory {root}")
    return records


def collect_inventory(args: argparse.Namespace, side: str, report: Path,
                      manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    host = args.source_host if side == "source" else args.target_host
    root = args.source_root if side == "source" else args.target_root
    if host:
        log(f"{side}: inventory source SSH {host}")
        return remote_inventory(args, side, report, manifest)
    log(f"{side}: inventory source local rootfs {root}")
    if side == "target":
        return local_target_inventory_with_sudo(args, report, manifest)
    return inventory(root, side, report, manifest)


def local_target_inventory_with_sudo(args: argparse.Namespace, report: Path,
                                     manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Read a local target through a narrowly scoped sudo helper."""
    command = [
        "sudo", "--", sys.executable, str(Path(__file__).resolve()),
        "--target-sudo-inventory-helper",
        "--target-root", str(args.target_root.resolve()),
        "--manifest", str(args.manifest.resolve()),
        "--report-dir", str(report.resolve()),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError("sudo target inventory helper failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"invalid target inventory helper output: {error}") from error


def apply_target_with_sudo(args: argparse.Namespace, report: Path) -> None:
    """Run only the local target apply phase through sudo."""
    command = [
        "sudo", "--", sys.executable, str(Path(__file__).resolve()),
        "--target-sudo-apply-helper",
        "--target-root", str(args.target_root.resolve()),
        "--manifest", str(args.manifest.resolve()),
        "--plan-file", str(args.plan_file.resolve()),
        "--report-dir", str(report.resolve()),
        "--yes",
    ]
    result = subprocess.run(command, check=False)
    if result.returncode:
        raise RuntimeError("sudo target apply helper failed")


def write_comparison(source: list[dict[str, str]], target: list[dict[str, str]], report: Path) -> None:
    sm, tm = {x["path"]: x for x in source}, {x["path"]: x for x in target}
    with (report / "comparison.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("path", "status", "class", "reason"))
        for path in sorted(set(sm) | set(tm)):
            if path in sm and sm[path]["type"] == "missing":
                status, reason = "missing-on-source", sm[path]["decision"]
            elif path in tm and tm[path]["type"] == "missing":
                status, reason = "missing-on-target", tm[path]["decision"]
            elif path not in tm: status, reason = "missing-on-target", "source-only"
            elif path not in sm: status, reason = "target-only", "protect-target"
            elif sm[path] == tm[path]: status, reason = "identical", "no-change"
            else: status, reason = "different", "metadata-or-content"
            writer.writerow((path, status, (sm.get(path) or tm[path])["class"], reason))


def directory_fingerprint(records: list[dict[str, str]], directory: str) -> tuple[int, int, str]:
    prefix = directory.rstrip("/") + "/"
    members = [record for record in records if record["path"].startswith(prefix)]
    total_size = sum(int(record["size"]) for record in members if record["type"] == "regular file")
    tree_hash = hashlib.sha256()
    for record in sorted(members, key=lambda item: item["path"]):
        tree_hash.update("\0".join((record["path"][len(prefix):], record["type"], record["size"], record["sha256"])).encode())
        tree_hash.update(b"\n")
    return len(members), total_size, tree_hash.hexdigest()


def write_directory_comparison(source: list[dict[str, str]], target: list[dict[str, str]],
                               report: Path, manifest: list[tuple[str, str]]) -> None:
    directories = sorted({path.rstrip("/"): cls for path, cls in manifest
                           if path.endswith("/") and cls != "A!"}.items())
    if not directories:
        return
    output = report / "directory-comparison.tsv"
    detail_output = report / "directory-files.tsv"
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("directory", "class", "status", "source_files", "target_files", "source_bytes", "target_bytes",
                         "source_tree_sha256", "target_tree_sha256"))
        with detail_output.open("w", newline="") as detail_stream:
            detail_writer = csv.writer(detail_stream, delimiter="\t", lineterminator="\n")
            detail_writer.writerow(("directory", "path", "status", "source_sha256", "target_sha256", "source_size", "target_size"))
            for directory, cls in directories:
                source_members = {x["path"]: x for x in source if x["path"].startswith(directory + "/")}
                target_members = {x["path"]: x for x in target if x["path"].startswith(directory + "/")}
                for path in sorted(set(source_members) | set(target_members)):
                    left, right = source_members.get(path), target_members.get(path)
                    if left is None:
                        status = "missing-on-source"
                    elif right is None:
                        status = "missing-on-target"
                    elif (left["type"], left["size"], left["sha256"]) == (right["type"], right["size"], right["sha256"]):
                        status = "identical"
                    else:
                        status = "different"
                    detail_writer.writerow((directory, path, status, left["sha256"] if left else "MISSING",
                                             right["sha256"] if right else "MISSING", left["size"] if left else "MISSING",
                                             right["size"] if right else "MISSING"))
                source_count, source_size, source_hash = directory_fingerprint(source, directory)
                target_count, target_size, target_hash = directory_fingerprint(target, directory)
                if not source_count and target_count:
                    status = "missing-on-source"
                elif source_count and not target_count:
                    status = "missing-on-target"
                elif (source_count, source_size, source_hash) == (target_count, target_size, target_hash):
                    status = "identical"
                else:
                    status = "different"
                writer.writerow((directory, cls, status, source_count, target_count, source_size, target_size,
                                 source_hash, target_hash))
                log(f"directory check {directory}: {status} (source files={source_count}, target files={target_count})")


def write_html_report(report: Path) -> None:
    tables = ("version-comparison.tsv", "migration-plan.tsv", "directory-comparison.tsv", "directory-files.tsv", "comparison.tsv")
    sections = []
    for filename in tables:
        path = report / filename
        if not path.exists():
            continue
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream, delimiter="\t"))
        if not rows:
            continue
        header, body = rows[0], rows[1:]
        table = [f"<h2>{html.escape(filename)}</h2><table><thead><tr>"]
        table.extend(f"<th>{html.escape(cell)}</th>" for cell in header)
        table.append("</tr></thead><tbody>")
        for row in body:
            table.append("<tr>")
            table.extend(f"<td>{html.escape(cell)}</td>" for cell in row)
            table.append("</tr>")
        table.append("</tbody></table>")
        sections.append("".join(table))
    content = "".join(sections)
    (report / "migration-report.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Configuration migration report</title>"
        "<style>body{font:14px sans-serif;margin:2em}table{border-collapse:collapse;margin-bottom:2em}"
        "th,td{border:1px solid #bbb;padding:5px;text-align:left;white-space:nowrap}"
        "th{background:#eee;position:sticky;top:0}tr:hover{background:#ffffcc}</style>" + content,
        encoding="utf-8",
    )


def organize_report(report: Path) -> Path:
    info = report.parent / f"{report.name}-info"
    info.mkdir(parents=True, exist_ok=True)
    keep = {
        "migration-plan.tsv", "source-migration.tar",
        "source-build-info", "source-build-layers",
        "target-build-info", "target-build-layers", "apply-results.tsv",
    }
    for entry in list(report.iterdir()):
        if entry.name in keep:
            continue
        destination = info / entry.name
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        shutil.move(str(entry), str(destination))
    return info


def make_plan(source: list[dict[str, str]], target: list[dict[str, str]], report: Path, manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    sm, tm = {x["path"]: x for x in source}, {x["path"]: x for x in target}
    plan = []
    for path, record in sorted(sm.items()):
        if record["type"] == "symbolic link" and record["class"] == "A!":
            if path not in tm or record["sha256"] != tm[path]["sha256"]:
                plan.append({"path": path, "action": "copy-symlink", "class": "A!",
                             "reason": "opaque directory link", "source_sha256": record["sha256"],
                             "target_sha256": tm[path]["sha256"] if path in tm else "MISSING",
                             "source_mode": record["mode"], "source_uid": record["uid"],
                             "source_gid": record["gid"], "source_atime_ns": record["atime_ns"],
                             "source_mtime_ns": record["mtime_ns"], "backup_scope": "none"})
            continue
        if record["type"] == "opaque directory" and record["class"] == "A!":
            target_state = "PRESENT" if path in tm and tm[path]["type"] != "missing" else "MISSING"
            plan.append({"path": path, "action": "copy-opaque-directory", "class": "A!",
                         "reason": "replace complete directory package", "source_sha256": "OPAQUE",
                         "target_sha256": target_state, "source_mode": record["mode"],
                         "source_uid": record["uid"], "source_gid": record["gid"],
                         "source_atime_ns": record["atime_ns"], "source_mtime_ns": record["mtime_ns"],
                         "backup_scope": "none"})
            continue
        # Symlinks are inventory data only.  Their link target may be outside
        # the selected manifest and there is no regular-file snapshot to use
        # safely for an executable copy operation.
        if record["type"] not in {"regular file", "symbolic link"}:
            continue
        if record["class"] == "A" and path not in tm:
            action = "copy-symlink" if record["type"] == "symbolic link" else "copy-new-file"
            plan.append({"path": path, "action": action, "class": "A", "reason": "missing on target", "source_sha256": record["sha256"], "target_sha256": "MISSING", "source_mode": record["mode"], "source_uid": record["uid"], "source_gid": record["gid"], "source_atime_ns": record["atime_ns"], "source_mtime_ns": record["mtime_ns"], "backup_scope": "none"})
        elif record["class"] == "A" and path in tm and record["sha256"] != tm[path]["sha256"]:
            action = "copy-symlink" if record["type"] == "symbolic link" else "copy-after-backup"
            plan.append({"path": path, "action": action, "class": "A", "reason": "textual candidate", "source_sha256": record["sha256"], "target_sha256": tm[path]["sha256"], "source_mode": record["mode"], "source_uid": record["uid"], "source_gid": record["gid"], "source_atime_ns": record["atime_ns"], "source_mtime_ns": record["mtime_ns"], "backup_scope": "none"})
        # Classes B, C and D are validation/reporting only.  They must not be
        # placed in migration-plan.tsv because that file is executable input
        # for --apply.
    with (report / "migration-plan.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("path", "action", "class", "reason", "source_sha256", "target_sha256", "source_mode", "source_uid", "source_gid", "source_atime_ns", "source_mtime_ns", "backup_scope"), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(plan)
    return plan


def make_diffs(plan: list[dict[str, str]], report: Path, manifest: list[tuple[str, str]]) -> None:
    explicit = {path for path, _ in manifest if not path.endswith("/")}
    source_archive = report / "source-analysis.tar"
    target_archive = report / "target-analysis.tar"
    if not source_archive.exists() or not target_archive.exists():
        return
    source_root = Path(tempfile.mkdtemp(prefix="migrate-diff-source-"))
    target_root = Path(tempfile.mkdtemp(prefix="migrate-diff-target-"))
    try:
        safe_extract(source_archive, source_root)
        safe_extract(target_archive, target_root)
        for item in plan:
            if item["action"] not in {"copy-after-backup", "copy-new-file"} or item["path"] not in explicit:
                continue
            path = item["path"]
            source = source_root / path.lstrip("/")
            target = target_root / path.lstrip("/")
            if source.is_file() and target.is_file():
                # Show the operation in migration direction: current target
                # first, desired source content second.  Therefore '+' means
                # content that will be present on target after migration.
                lines = difflib.unified_diff(target.read_text(errors="replace").splitlines(True), source.read_text(errors="replace").splitlines(True), fromfile=f"target:{path}", tofile=f"source:{path}")
                output = report / "diffs" / f"{path.lstrip('/')}.diff"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("".join(lines))
    finally:
        shutil.rmtree(source_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)


def remote_hash(args: argparse.Namespace, target: str) -> str | None:
    quoted = shlex.quote(target)
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-p", str(args.target_port), *( ["-i", args.target_identity] if args.target_identity else []), "--", f"{args.target_user}@{args.target_host}", f"if [ -L {quoted} ]; then printf 'SYMLINK:%s\\n' \"$(readlink {quoted})\"; elif [ -d {quoted} ]; then printf 'OPAQUE\\n'; else sha256sum -- {quoted} | awk '{{print $1}}'; fi"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if result.returncode:
        return None
    return result.stdout.strip()


def apply_plan_files(args: argparse.Namespace, report: Path) -> None:
    results = report / "apply-results.tsv"
    result_stream = results.open("w", newline="")
    result_writer = csv.writer(result_stream, delimiter="\t", lineterminator="\n")
    result_writer.writerow(("path", "status", "expected_target_sha256", "actual_before", "actual_after", "backup"))
    log(f"applying approved plan: {args.plan_file}")
    if Path(args.plan_file).resolve() != (report / "migration-plan.tsv").resolve():
        fail("plan file must belong to the selected report directory")
    backed_up: dict[str, str] = {}
    temporary_source = tempfile.TemporaryDirectory(prefix="migrate-apply-source-")
    source_root = Path(temporary_source.name)
    safe_extract(report / "source-migration.tar", source_root)
    try:
      with (Path(args.plan_file)).open(newline="") as stream:
        plan_items = list(csv.DictReader(stream, delimiter="\t"))

      # Validate the complete target before changing anything.  This avoids a
      # partial apply when one later file was added or changed after planning.
      for item in plan_items:
        if item["action"] not in {"copy-after-backup", "copy-new-file", "copy-symlink", "copy-opaque-directory"}:
            continue
        path = item["path"]
        source = source_root / path.lstrip("/")
        if item["action"] == "copy-opaque-directory":
            actual_before = ("PRESENT" if ((args.target_root / path.lstrip("/")).is_dir()
                             if not args.target_host else
                             subprocess.run(["ssh", "-o", "BatchMode=yes", "-p", str(args.target_port),
                                             *( ["-i", args.target_identity] if args.target_identity else []), "--",
                                             f"{args.target_user}@{args.target_host}",
                                             f"test -d {shlex.quote('/' + path.lstrip('/'))}"],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                            check=False).returncode == 0)
                           else "MISSING")
            if actual_before != item["target_sha256"]:
                fail(f"target changed since plan: {path} (expected {item['target_sha256']}, got {actual_before})")
            if not source.is_dir():
                fail(f"source snapshot has no opaque directory: {path}")
            continue
        is_symlink = item["action"] == "copy-symlink"
        for field in ("source_mode", "source_uid", "source_gid", "source_atime_ns", "source_mtime_ns"):
            if not item.get(field):
                fail(f"plan has no {field}: {path}; regenerate the plan")
        checksum = digest(source) if is_symlink else hashlib.sha256(source.read_bytes()).hexdigest()
        if checksum != item["source_sha256"]:
            fail(f"source snapshot changed since plan: {path}")
        if args.target_host:
            actual_before = remote_hash(args, "/" + path.lstrip("/")) or "MISSING"
        else:
            target = args.target_root / path.lstrip("/")
            if target.is_symlink():
                actual_before = digest(target)
            elif target.is_dir():
                actual_before = "OPAQUE"
            else:
                actual_before = digest(target) if target.exists() else "MISSING"
        if actual_before != item["target_sha256"]:
            fail(f"target changed since plan: {path} (expected {item['target_sha256']}, got {actual_before})")
      log(f"apply preflight passed: {len(plan_items)} plan entries unchanged")

      for item in plan_items:
            if item["action"] not in {"copy-after-backup", "copy-new-file", "copy-symlink", "copy-opaque-directory"}:
                continue
            path = item["path"]
            if not safe_path(path) or item["class"] not in {"A", "A!"}:
                fail(f"unsafe plan entry: {path}")
            if item["action"] == "copy-opaque-directory":
                source = source_root / path.lstrip("/")
                if not source.is_dir():
                    fail(f"source snapshot has no opaque directory: {path}")
                log(f"apply {path}: sending complete directory package (including hidden files)")
                with tempfile.NamedTemporaryFile(prefix="migrate-opaque-", suffix=".tar", delete=False) as temporary:
                    package = Path(temporary.name)
                try:
                    create_opaque_package(report / "source-migration.tar", path, package)
                except Exception:
                    package.unlink(missing_ok=True)
                    raise
                if not args.target_host:
                    target = args.target_root / path.lstrip("/")
                    if target.exists() or target.is_symlink():
                        if target.is_dir() and not target.is_symlink():
                            shutil.rmtree(target)
                        else:
                            target.unlink()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    extract_opaque_package(package, args.target_root)
                    result_writer.writerow((path, "applied", item["target_sha256"], item["target_sha256"],
                                            "OPAQUE", "none (source is the controlled Yocto artifact)"))
                    result_stream.flush()
                else:
                    try:
                        target = "/" + path.lstrip("/")
                        command = f"rm -rf -- {shlex.quote(target)}; mkdir -p -- {shlex.quote(str(Path(target).parent))}; tar -xf - -C /"
                        ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity,
                                    command, input_file=package)
                        result_writer.writerow((path, "applied", item["target_sha256"], item["target_sha256"],
                                                "OPAQUE", "none (source is the controlled Yocto artifact)"))
                        result_stream.flush()
                    finally:
                        package.unlink(missing_ok=True)
                if not args.target_host:
                    package.unlink(missing_ok=True)
                log(f"apply {path}: complete directory package applied")
                continue
            if not item.get("backup_scope"):
                fail(f"plan has no backup_scope: {path}; regenerate the plan")
            for field in ("source_mode", "source_uid", "source_gid", "source_atime_ns", "source_mtime_ns"):
                if not item.get(field):
                    fail(f"plan has no {field}: {path}; regenerate the plan")
            source = source_root / path.lstrip("/")
            is_symlink = item["action"] == "copy-symlink"
            data = None if is_symlink else source.read_bytes()
            checksum = digest(source) if is_symlink else hashlib.sha256(data).hexdigest()
            if checksum != item["source_sha256"]:
                fail(f"source snapshot changed since plan: {path}")
            log(f"apply {path}: checking target before write")
            if not args.target_host:
                target = args.target_root / path.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink():
                    actual_before = digest(target)
                elif target.is_dir():
                    actual_before = "OPAQUE"
                else:
                    actual_before = digest(target) if target.exists() else "MISSING"
                if actual_before != item["target_sha256"]:
                    fail(f"target changed since plan: {path} (expected {item['target_sha256']}, got {actual_before})")
                scope = item["backup_scope"]
                if scope not in backed_up:
                    backed_up[scope] = "none (source is the controlled Yocto artifact)"
                if is_symlink:
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink(missing_ok=True)
                    target.symlink_to(os.readlink(source))
                else:
                    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".migrate-config.", delete=False) as temporary:
                        temporary.write(data); temporary_path = Path(temporary.name)
                    if hashlib.sha256(temporary_path.read_bytes()).hexdigest() != checksum:
                        fail(f"local temporary copy verification failed: {path}")
                    os.replace(temporary_path, target)
                os.chown(target, int(item["source_uid"]), int(item["source_gid"]), follow_symlinks=False)
                if not is_symlink:
                    os.chmod(target, int(item["source_mode"], 8), follow_symlinks=False)
                    os.utime(target, ns=(int(item["source_atime_ns"]), int(item["source_mtime_ns"])), follow_symlinks=False)
                actual_after = digest(target)
                result_writer.writerow((path, "applied", item["target_sha256"], actual_before, actual_after, backed_up[scope])); result_stream.flush()
                log(f"apply {path}: applied, verified sha256={actual_after}, backup-scope={scope}")
                continue
            target = "/" + path.lstrip("/")
            quoted = shlex.quote(target)
            actual_before = remote_hash(args, target) or "MISSING"
            if actual_before != item["target_sha256"]:
                fail(f"target changed since plan: {path} (expected {item['target_sha256']}, got {actual_before})")
            scope = item["backup_scope"]
            if scope not in backed_up:
                backed_up[scope] = "none (source is the controlled Yocto artifact)"
            parent = shlex.quote(str(Path(target).parent)); temporary = shlex.quote(str(Path(target).parent / f".migrate-config.{os.getpid()}.tmp"))
            if is_symlink:
                uid = shlex.quote(item["source_uid"])
                gid = shlex.quote(item["source_gid"])
                command = f"mkdir -p {parent}; rm -rf -- {quoted}; ln -s -- {shlex.quote(os.readlink(source))} {quoted}; chown -h {uid}:{gid} {quoted}"
                ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, command)
            else:
                mode = shlex.quote(item["source_mode"])
                uid = shlex.quote(item["source_uid"])
                gid = shlex.quote(item["source_gid"])
                atime = shlex.quote("@" + item["source_atime_ns"][:-9] + "." + item["source_atime_ns"][-9:])
                mtime = shlex.quote("@" + item["source_mtime_ns"][:-9] + "." + item["source_mtime_ns"][-9:])
                command = f"test ! -L {quoted}; mkdir -p {parent}; cat > {temporary}; test $(sha256sum -- {temporary} | awk '{{print $1}}') = {checksum}; chown {uid}:{gid} {temporary}; chmod {mode} {temporary}; touch -a -d {atime} {temporary}; touch -m -d {mtime} {temporary}; mv -f -- {temporary} {quoted}"
                ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, command, data)
            actual_after = remote_hash(args, target)
            if actual_after != checksum:
                fail(f"remote write verification failed: {path}")
            result_writer.writerow((path, "applied", item["target_sha256"], actual_before, actual_after, backed_up[scope])); result_stream.flush()
            log(f"apply {path}: applied, verified sha256={actual_after}, backup-scope={scope}")
      result_stream.close()
    finally:
      temporary_source.cleanup()


def service_status(args: argparse.Namespace, service: str) -> str:
    command = f"systemctl is-active -- {shlex.quote(service)} || true"
    return ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, command).decode().strip()


def verify_target_version(args: argparse.Namespace, report: Path) -> None:
    for version_file in VERSION_FILES:
        filename = f"target-{Path(version_file).name}"
        expected = (report / filename).read_bytes()
        actual = read_version(args, "target", version_file)
        if actual != expected:
            fail(f"target system version changed since report generation: {version_file}")


def apply_plan(args: argparse.Namespace, report: Path) -> None:
    if not args.target_host:
        verify_target_version(args, report)
        apply_plan_files(args, report)
        return

    verify_target_version(args, report)

    active = []
    for service in MIGRATION_SERVICES:
        status = service_status(args, service)
        log(f"service {service}: {status or 'unknown'}")
        if status == "active":
            active.append(service)

    stopped = []
    try:
        for service in active:
            log(f"stopping service: {service}")
            ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, f"systemctl stop -- {shlex.quote(service)}")
            stopped.append(service)
        apply_plan_files(args, report)
    finally:
        for service in reversed(stopped):
            try:
                log(f"starting service: {service}")
                ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, f"systemctl start -- {shlex.quote(service)}")
            except RuntimeError as error:
                log(f"could not restart {service}: {error}")


def main() -> int:
    global VERBOSE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_const", const="inventory", dest="mode", default="report")
    for mode in ("report", "plan", "diff", "dry-run", "apply"):
        parser.add_argument(f"--{mode}", action="store_const", const=mode, dest="mode")
    for prefix in ("source", "target"):
        parser.add_argument(f"--{prefix}-host", help=f"{prefix} SSH host; omit to use --{prefix}-root")
        parser.add_argument(f"--{prefix}-user", default="")
        parser.add_argument(f"--{prefix}-port", type=int, default=22); parser.add_argument(f"--{prefix}-identity", default="")
        parser.add_argument(f"--{prefix}-root", type=Path, default=None,
                            help=f"{prefix} unpacked rootfs directory when --{prefix}-host is omitted")
    parser.add_argument("--source-read-only-verified", action="store_true")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--plan-file", type=Path)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--target-sudo-inventory-helper", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--target-sudo-apply-helper", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--verbose", action="store_true", help="show detailed progress (default)")
    parser.add_argument("--quiet", action="store_true", help="only show errors and final report")
    args = parser.parse_args()
    VERBOSE = not args.quiet
    if args.source_host and args.source_root is not None:
        fail("choose either --source-host or --source-root, not both")
    if args.target_host and args.target_root is not None:
        fail("choose either --target-host or --target-root, not both")
    if args.target_sudo_inventory_helper:
        if args.target_root is None:
            fail("target inventory helper requires --target-root")
        manifest = read_manifest(args.manifest)
        with tempfile.TemporaryDirectory(prefix="migrate-target-inventory-") as temporary:
            helper_report = args.report_dir or Path(temporary)
            records = inventory(args.target_root, "target", helper_report, manifest)
        create_analysis_archive(args.target_root, records, args.report_dir, "target-analysis.tar")
        json.dump(records, sys.stdout)
        return 0
    if args.target_sudo_apply_helper:
        if not args.plan_file or not args.yes:
            fail("target apply helper requires --plan-file and --yes")
        report = args.report_dir or args.plan_file.parent
        verify_target_version(args, report)
        apply_plan_files(args, report)
        return 0
    if not args.target_host and args.target_root is None:
        fail("target is required: provide --target-host or --target-root")
    if args.mode != "apply" and not args.source_host and args.source_root is None:
        fail("source is required: provide --source-host or --source-root")
    if args.mode == "apply" and (not args.yes or not args.plan_file): fail("--apply requires --yes and --plan-file")
    report = args.plan_file.parent if args.mode == "apply" else (
        args.report_dir or DEFAULT_REPORT_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    )
    report.mkdir(parents=True, exist_ok=True); (report / "diffs").mkdir(exist_ok=True)
    manifest = read_manifest(args.manifest)
    log(f"migration manifest: {args.manifest} ({len(manifest)} explicit files)")
    log(f"report directory: {report}")
    log("mode: " + args.mode)
    if args.mode == "apply":
        if args.target_host:
            apply_plan(args, report)
        else:
            apply_target_with_sudo(args, report)
        print(f"report: {report}\nresults: {report / 'apply-results.tsv'}")
        return 0
    save_versions(args, report)
    if args.source_host:
        log(f"source: SSH {args.source_user}@{args.source_host}:{args.source_port}")
    else:
        log(f"source: local rootfs {args.source_root}")
    if args.target_host:
        log(f"target: SSH {args.target_user}@{args.target_host}:{args.target_port}")
    else:
        log(f"target: local rootfs {args.target_root}")
    source = collect_inventory(args, "source", report, manifest)
    if not args.source_host:
        create_analysis_archive(args.source_root, source, report, "source-analysis.tar")
    target = collect_inventory(args, "target", report, manifest)
    log(f"inventory complete: source={len(source)} target={len(target)}")
    write_comparison(source, target, report)
    write_directory_comparison(source, target, report, manifest)
    plan = make_plan(source, target, report, manifest)
    create_migration_archive(report, plan)
    make_diffs(plan, report, manifest)
    write_html_report(report)
    log(f"comparison complete: {len(plan)} plan entries")
    (report / "migration-report.md").write_text(f"# Configuration migration report\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\nSecrets and runtime data are excluded.\n")
    info_report = organize_report(report)
    if args.mode == "dry-run":
        for item in plan: print("would:", "\t".join(item.values()))
    print(f"report: {report}\ninfo: {info_report}\nplan: {report / 'migration-plan.tsv'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        fail(str(error))
