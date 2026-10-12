#!/usr/bin/env python3
"""Safe, host-side configuration inventory and migration over SSH."""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
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
MIGRATION_SERVICES = (
    "mpd", "snapserver", "snapclient", "minidlna", "pulseaudio",
    "transmission-daemon", "smbd", "jellyfin",
)
FIELDS = ("path", "type", "mode", "uid", "gid", "size", "sha256", "class", "decision")
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
            if len(fields) != 2 or fields[0] not in {"A", "B", "C", "D"} or not safe_path(fields[1]):
                fail(f"invalid manifest entry {path}:{number}; expected '<class> <absolute-path>'")
            entries.append((fields[1], fields[0]))
    if not entries:
        fail(f"migration manifest is empty: {path}")
    return entries


def classify(path: str, manifest: dict[str, str]) -> tuple[str, str, str]:
    if path not in manifest:
        fail(f"path is missing from migration manifest: {path}")
    cls = manifest[path]
    descriptions = {
        "A": "safe service configuration",
        "B": "requires manual verification",
        "C": "network, access, or device identity",
        "D": "secret, runtime, or application data",
    }
    decisions = {
        "A": "compare and back up target",
        "B": "manual review",
        "C": "do not overwrite automatically",
        "D": "do not migrate automatically",
    }
    return cls, descriptions[cls], decisions[cls]


def ssh_command(host: str, user: str, port: int, identity: str, command: str, data: bytes | None = None) -> bytes:
    destination = f"{user}@{host}" if user else host
    args = ["ssh", "-o", "BatchMode=yes", "-o", "RequestTTY=no", "-o", "ClearAllForwardings=yes", "-p", str(port)]
    if identity:
        args += ["-i", identity]
    args += ["--", destination, command]
    log(f"SSH start: {destination}  command={command!r}")
    if data is not None:
        log(f"SSH stdin: {len(data)} bytes")
    started = time.monotonic()
    with tempfile.TemporaryFile() as error_stream:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_stream)
        if data is not None and process.stdin is not None:
            process.stdin.write(data)
            process.stdin.close()
        output_parts = []
        output_size = 0
        last_report = time.monotonic()
        while process.stdout is not None:
            chunk = process.stdout.read(1024 * 1024)
            if not chunk:
                break
            output_parts.append(chunk)
            output_size += len(chunk)
            if time.monotonic() - last_report >= 1:
                log(f"SSH progress: {destination} stdout={output_size} bytes")
                last_report = time.monotonic()
        process.wait()
        error_stream.seek(0)
        stderr = error_stream.read()
    stdout = b"".join(output_parts)
    elapsed = time.monotonic() - started
    log(f"SSH end: {destination}  exit={process.returncode} stdout={len(stdout)} bytes elapsed={elapsed:.1f}s")
    if process.returncode:
        raise RuntimeError(f"SSH command failed on {destination}: {stderr.decode(errors='replace').strip()}")
    return stdout


def expanded_manifest(root: Path, manifest: list[tuple[str, str]]) -> list[tuple[str, str]]:
    expanded = []
    known = {path for path, _ in expanded}
    for path, cls in manifest:
        candidate = root / path.lstrip("/")
        if candidate.is_dir() and not candidate.is_symlink():
            for directory, directories, files in os.walk(candidate, followlinks=False):
                directories[:] = [name for name in directories if not (Path(directory) / name).is_symlink()]
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
    for item, _ in manifest:
        current = root / item.lstrip("/")
        if current.is_file() or current.is_symlink():
            found.append(current)
    return found


def digest(path: Path) -> str:
    if path.is_symlink():
        return "SYMLINK"
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inventory(root: Path, side: str, report: Path, manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    records = []
    manifest = expanded_manifest(root, manifest)
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
            kind = "symbolic link" if stat.S_ISLNK(info.st_mode) else "regular file"
            cls, reason, decision = classify(relative, manifest_map)
            record = {"path": relative, "type": kind, "mode": oct(info.st_mode & 0o7777)[2:],
                      "uid": str(info.st_uid), "gid": str(info.st_gid), "size": str(info.st_size),
                      "sha256": digest(file_path), "class": cls, "decision": f"{reason}; {decision}"}
            writer.writerow(record)
            records.append(record)
            if index % 100 == 0:
                log(f"{side}: analyzed {index}/{len(files)} entries")
            if kind == "regular file" and cls != "D":
                target = report / side / "files" / relative.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target)
    return records


def safe_extract(data: bytes, destination: Path) -> None:
    log(f"extracting remote archive: {len(data)} bytes -> {destination}")
    with tarfile.open(fileobj=__import__("io").BytesIO(data), mode="r:") as archive:
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
    # BusyBox tar commonly lacks GNU tar's --null option. The allowlisted
    # paths contain neither whitespace nor newlines, so newline-delimited -T
    # input is portable across the supported Yocto userspaces.
    log(f"{side}: preparing remote inventory; {len(manifest)} explicit files")
    names = ("\n".join(path for path, _ in manifest) + "\n").encode()
    for index, (path, cls) in enumerate(manifest, 1):
        log(f"{side}: manifest[{index}] {cls} {path}")
    command = "while IFS= read -r p; do if [ -e \"$p\" ] || [ -L \"$p\" ]; then printf '%s\\n' \"$p\"; if [ -L \"$p\" ]; then q=$(readlink -f \"$p\" 2>/dev/null || true); case \"$q\" in /*) if [ -f \"$q\" ]; then printf '%s\\n' \"$q\"; fi;; esac; fi; fi; done | tar -C / -cf - -T -"
    archive = ssh_command(host, user, port, identity, command, names)
    root = report / side / "root"
    root.mkdir(parents=True)
    safe_extract(archive, root)
    records = inventory(root, side, report, manifest)
    shutil.rmtree(root)
    log(f"{side}: removed temporary extraction directory {root}")
    return records


def write_comparison(source: list[dict[str, str]], target: list[dict[str, str]], report: Path) -> None:
    sm, tm = {x["path"]: x for x in source}, {x["path"]: x for x in target}
    with (report / "comparison.tsv").open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("path", "status", "class", "reason"))
        for path in sorted(set(sm) | set(tm)):
            if path not in tm: status, reason = "missing-on-target", "source-only"
            elif path not in sm: status, reason = "target-only", "protect-target"
            elif sm[path] == tm[path]: status, reason = "identical", "no-change"
            else: status, reason = "different", "metadata-or-content"
            writer.writerow((path, status, (sm.get(path) or tm[path])["class"], reason))


def backup_scope(path: str, manifest: list[tuple[str, str]]) -> str:
    directories = [entry.rstrip("/") for entry, _ in manifest if entry.endswith("/") and path.startswith(entry)]
    return max(directories, key=len) if directories else path


def make_plan(source: list[dict[str, str]], target: list[dict[str, str]], report: Path, manifest: list[tuple[str, str]]) -> list[dict[str, str]]:
    sm, tm = {x["path"]: x for x in source}, {x["path"]: x for x in target}
    plan = []
    for path, record in sorted(sm.items()):
        if record["class"] == "A" and path not in tm:
            plan.append({"path": path, "action": "copy-new-file", "class": "A", "reason": "missing on target", "source_sha256": record["sha256"], "target_sha256": "MISSING", "backup_scope": backup_scope(path, manifest)})
        elif record["class"] == "A" and path in tm and record["sha256"] != tm[path]["sha256"]:
            plan.append({"path": path, "action": "copy-after-backup", "class": "A", "reason": "textual candidate", "source_sha256": record["sha256"], "target_sha256": tm[path]["sha256"], "backup_scope": backup_scope(path, manifest)})
        elif record["class"] != "A":
            plan.append({"path": path, "action": "do-not-migrate", "class": record["class"], "reason": record["decision"], "source_sha256": record["sha256"], "target_sha256": tm.get(path, {}).get("sha256", "MISSING"), "backup_scope": backup_scope(path, manifest)})
    with (report / "migration-plan.tsv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("path", "action", "class", "reason", "source_sha256", "target_sha256", "backup_scope"), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(plan)
    return plan


def make_diffs(plan: list[dict[str, str]], report: Path) -> None:
    for item in plan:
        if item["action"] not in {"copy-after-backup", "copy-new-file"}:
            continue
        path = item["path"]
        source = report / "source" / "files" / path.lstrip("/")
        target = report / "target" / "files" / path.lstrip("/")
        if source.is_file() and target.is_file():
            lines = difflib.unified_diff(source.read_text(errors="replace").splitlines(True), target.read_text(errors="replace").splitlines(True), fromfile=f"source:{path}", tofile=f"target:{path}")
            output = report / "diffs" / f"{path.lstrip('/')}.diff"
            output.parent.mkdir(parents=True, exist_ok=True); output.write_text("".join(lines))


def remote_hash(args: argparse.Namespace, target: str) -> str | None:
    quoted = shlex.quote(target)
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-p", str(args.target_port), *( ["-i", args.target_identity] if args.target_identity else []), "--", f"{args.target_user}@{args.target_host}", f"test ! -L {quoted} && sha256sum -- {quoted} | awk '{{print $1}}'"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if result.returncode:
        return None
    return result.stdout.strip()


def backup_scope_local(args: argparse.Namespace, report: Path, scope: str) -> str:
    target = args.target_root / scope.lstrip("/")
    backup = report / "backup" / scope.lstrip("/")
    if not target.exists() and not target.is_symlink():
        return "none"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if target.is_dir() and not target.is_symlink():
        shutil.copytree(target, backup, symlinks=True, dirs_exist_ok=True)
    elif target.is_symlink():
        backup.symlink_to(os.readlink(target))
    else:
        shutil.copy2(target, backup)
    log(f"backup created: {scope} -> {backup}")
    return str(backup)


def backup_scope_remote(args: argparse.Namespace, report: Path, scope: str) -> str:
    target = "/" + scope.lstrip("/")
    quoted = shlex.quote(target)
    exists = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-p", str(args.target_port), *( ["-i", args.target_identity] if args.target_identity else []), "--", f"{args.target_user}@{args.target_host}", f"test -e {quoted} || test -L {quoted}"],
        check=False,
    ).returncode == 0
    if not exists:
        return "none"
    archive = ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, f"tar -C / -cf - -- {shlex.quote(scope.lstrip('/'))}")
    backup = report / "backup"
    backup.mkdir(parents=True, exist_ok=True)
    safe_extract(archive, backup)
    log(f"backup created: {scope} -> {backup}")
    return str(backup / scope.lstrip("/"))


def apply_plan_files(args: argparse.Namespace, report: Path) -> None:
    results = report / "apply-results.tsv"
    result_stream = results.open("w", newline="")
    result_writer = csv.writer(result_stream, delimiter="\t", lineterminator="\n")
    result_writer.writerow(("path", "status", "expected_target_sha256", "actual_before", "actual_after", "backup"))
    log(f"applying approved plan: {args.plan_file}")
    if Path(args.plan_file).resolve() != (report / "migration-plan.tsv").resolve():
        fail("plan file must belong to the selected report directory")
    backed_up: dict[str, str] = {}
    with (Path(args.plan_file)).open(newline="") as stream:
        for item in csv.DictReader(stream, delimiter="\t"):
            if item["action"] not in {"copy-after-backup", "copy-new-file"}:
                continue
            path = item["path"]
            if not safe_path(path) or item["class"] != "A":
                fail(f"unsafe plan entry: {path}")
            if not item.get("backup_scope"):
                fail(f"plan has no backup_scope: {path}; regenerate the plan")
            source = report / "source" / "files" / path.lstrip("/")
            data = source.read_bytes()
            checksum = hashlib.sha256(data).hexdigest()
            if checksum != item["source_sha256"]:
                fail(f"source snapshot changed since plan: {path}")
            log(f"apply {path}: checking target before write")
            if not args.target_host:
                target = args.target_root / path.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                actual_before = digest(target) if target.exists() and not target.is_symlink() else "MISSING"
                if actual_before != item["target_sha256"]:
                    fail(f"target changed since plan: {path} (expected {item['target_sha256']}, got {actual_before})")
                scope = item["backup_scope"]
                if scope not in backed_up:
                    backed_up[scope] = backup_scope_local(args, report, scope)
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".migrate-config.", delete=False) as temporary:
                    temporary.write(data); temporary_path = Path(temporary.name)
                if hashlib.sha256(temporary_path.read_bytes()).hexdigest() != checksum:
                    fail(f"local temporary copy verification failed: {path}")
                os.replace(temporary_path, target)
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
                backed_up[scope] = backup_scope_remote(args, report, scope)
            parent = shlex.quote(str(Path(target).parent)); temporary = shlex.quote(str(Path(target).parent / f".migrate-config.{os.getpid()}.tmp"))
            command = f"test ! -L {quoted}; mkdir -p {parent}; cat > {temporary}; test $(sha256sum -- {temporary} | awk '{{print $1}}') = {checksum}; mv -f -- {temporary} {quoted}"
            ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, command, data)
            actual_after = remote_hash(args, target)
            if actual_after != checksum:
                fail(f"remote write verification failed: {path}")
            result_writer.writerow((path, "applied", item["target_sha256"], actual_before, actual_after, backed_up[scope])); result_stream.flush()
            log(f"apply {path}: applied, verified sha256={actual_after}, backup-scope={scope}")
    result_stream.close()


def service_status(args: argparse.Namespace, service: str) -> str:
    command = f"systemctl is-active -- {shlex.quote(service)} || true"
    return ssh_command(args.target_host, args.target_user, args.target_port, args.target_identity, command).decode().strip()


def apply_plan(args: argparse.Namespace, report: Path) -> None:
    if not args.target_host:
        apply_plan_files(args, report)
        return

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
        parser.add_argument(f"--{prefix}-host"); parser.add_argument(f"--{prefix}-user", default="")
        parser.add_argument(f"--{prefix}-port", type=int, default=22); parser.add_argument(f"--{prefix}-identity", default="")
        parser.add_argument(f"--{prefix}-root", type=Path, default=Path("/"))
    parser.add_argument("--source-read-only-verified", action="store_true")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--plan-file", type=Path)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="show detailed progress (default)")
    parser.add_argument("--quiet", action="store_true", help="only show errors and final report")
    args = parser.parse_args()
    VERBOSE = not args.quiet
    if bool(args.source_host) != bool(args.target_host): fail("source and target must both use SSH, or both use local roots for tests")
    if args.mode == "apply" and (not args.yes or not args.plan_file): fail("--apply requires --yes and --plan-file")
    report = args.plan_file.parent if args.mode == "apply" else (args.report_dir or Path("reports/config-migration") / datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S"))
    report.mkdir(parents=True, exist_ok=True); (report / "diffs").mkdir(exist_ok=True)
    manifest = read_manifest(args.manifest)
    log(f"migration manifest: {args.manifest} ({len(manifest)} explicit files)")
    log(f"report directory: {report}")
    log("mode: " + args.mode)
    if args.mode == "apply":
        apply_plan(args, report)
        print(f"report: {report}\nresults: {report / 'apply-results.tsv'}")
        return 0
    if args.source_host:
        log(f"source: SSH {args.source_user}@{args.source_host}:{args.source_port}")
        log(f"target: SSH {args.target_user}@{args.target_host}:{args.target_port}")
        source = remote_inventory(args, "source", report, manifest); target = remote_inventory(args, "target", report, manifest)
    else:
        log(f"source: local {args.source_root}")
        log(f"target: local {args.target_root}")
        source = inventory(args.source_root, "source", report, manifest); target = inventory(args.target_root, "target", report, manifest)
    log(f"inventory complete: source={len(source)} target={len(target)}")
    write_comparison(source, target, report); plan = make_plan(source, target, report, manifest); make_diffs(plan, report)
    log(f"comparison complete: {len(plan)} plan entries")
    (report / "migration-report.md").write_text(f"# Configuration migration report\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\nSecrets and runtime data are excluded.\n")
    if args.mode == "dry-run":
        for item in plan: print("would:", "\t".join(item.values()))
    print(f"report: {report}\nplan: {report / 'migration-plan.tsv'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        fail(str(error))
