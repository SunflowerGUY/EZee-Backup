import base64
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from coffee_support import add_coffee_link, show_support

try:
    import winsound
except ImportError:
    winsound = None

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

VERSION = "4.4"
APP_NAME = "EZee-Backup"
DRIVE_POLL_INTERVAL_MS = 60000  # slow safety-net poll; real-time detection comes from WM_DEVICECHANGE

SPLASH_B64 = (
    """/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCACTAZEDAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5ZoooruOcKK7zT/B2g6Vpy3fjXVrq2u5Vymk2KqbpAdpUyFshDtYnYwBxjnIK1L/avgL/AKJ5/wCVmf8Awrp+rcvxyUX2d7/gnb5nD9eUv4UJSXdWS+Tk1f1V0efUV6D/AGr4C/6J5/5WZ/8ACj+1fAX/AETz/wArM/8AhR7CH/Pxf+Tf/Ih9bq/8+ZffD/5M8+or0H+1fAX/AETz/wArM/8AhR/avgL/AKJ5/wCVmf8Awo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhR/avgL/onn/lZn/wo9hD/n4v/Jv/AJEPrdX/AJ8y++H/AMmefUV6D/avgL/onn/lZn/wo/tXwF/0Tz/ysz/4Uewh/wA/F/5N/wDIh9bq/wDPmX3w/wDkzz6ivQf7V8Bf9E8/8rM/+FH9q+Av+ief+Vmf/Cj2EP8An4v/ACb/AORD63V/58y++H/yZ59RXoP9q+Av+ief+Vmf/Cj+1fAX/RPP/KzP/hR7CH/Pxf8Ak3/yIfW6v/PmX3w/+TPPqK9B/tXwF/0Tz/ysz/4Uf2r4C/6J5/5WZ/8ACj2EP+fi/wDJv/kQ+t1f+fMvvh/8mefUV6D/AGr4C/6J5/5WZ/8ACj+1fAX/AETz/wArM/8AhR7CH/Pxf+Tf/Ih9bq/8+ZffD/5M8+or0H+1fAX/AETz/wArM/8AhR/avgL/AKJ5/wCVmf8Awo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhR/avgL/onn/lZn/wo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhR/avgL/onn/lZn/wo/tXwF/0Tz/ysz/4Uewh/wA/F/5N/wDIh9bq/wDPmX3w/wDkzz6ivQf7V8Bf9E8/8rM/+FH9q+Av+ief+Vmf/Cj2EP8An4v/ACb/AORD63V/58y++H/yZ59RXoP9q+Av+ief+Vmf/Cj+1fAX/RPP/KzP/hR7CH/Pxf8Ak3/yIfW6v/PmX3w/+TPPqK9B/tXwF/0Tz/ysz/4Uf2r4C/6J5/5WZ/8ACj2EP+fi/wDJv/kQ+t1f+fMvvh/8mefUV6D/AGr4C/6J5/5WZ/8ACj+1fAX/AETz/wArM/8AhR7CH/Pxf+Tf/Ih9bq/8+ZffD/5M8+or0H+1fAX/AETz/wArM/8AhR/avgL/AKJ5/wCVmf8Awo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhRJ4X8KeIbV38L6lPp2rHLLpeoOpSViVxHFLwOpKruyzYGdoyaaw3N8E0321X5pA8dya1acoru7NfPlbt6vQ8+op9xDLbzyQTxPFNGxSSN1KsjA4IIPIIPamVzHcncK7z4fWdlpXhfUfGt2iTXcE4s9JQ8hLkruMpUqQSqkMueMqeh2muDr0HW/8Akl3gr/t//wDR4row3u80+sVdet0vwvc4cd7yhS6SlZ+iTk187Wfkzmp5ZZ5nnkeWWRi7u7EszE5JJPUmmUUVznYlYKKKKQBRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAdV4hgt/E3w/k8RyN/xPNHkjhv5WY5uoHO2N2+XBcHC5znCksT8orzyvRPh3/qPFX/YuXn8lrzuuqu+aMJvdrX5dTjwa9nOpSWyd15Jrb0Tvby06BXoOt/8ku8Ff9v/AP6PFefV6Drf/JLvBX/b/wD+jxSofBU9P/bohi/4tH/E/wD0iZy9FFFcx2BRRRQAUUUUAFFFFABV7w+LFtbs01Jc2TzKk53EbUJwW49M5/CqNFNOzE1dWO1g8Hxf2Qpv547G4hncXMjSRg4Z2jjQCSRF6wTsec4K8EVUtvCtmQgutdiid9RurJCkatG/kIjFg7Oo+beFUHAJIyQDkZzeKNce/mvZbtJpplRZPNt43Rtn3TsZSu4f3sZySc5JzBDruqxNGwuy5jmmnHmIr7nmVVlLbgdwYKoIOR+ZrVyp9jnUK3839fd3Ny48JQwWct1Peyw29rJP57GzYTBUFtt+RnAJLXKjGQBgncwxUkfgu18ywhl1pll1K9FrZKtpuD7ooJI3c7xsBFwgIGSPesZvFGts6s92jAF/3ZtzHhkjQqU27Su2KMBcYGwYAqNvEWstd2t2bwma0uzeQN5a/JKfLGQMYxiKMBegC8DrRzU+wKFe3xf19xY8Hwabd3F9bX1k1xIbC6lgfzSqxNHbyyBsD7x3IuMnHXIOeL/AIT0rTbq20pLy0FxJq+qPYeYZGU2yhYvnUAgE5mz82RhOnNc1Y3dxZTNNayeXI0UkJO0H5JEZHHPqrMPx4q5Za9qlnE8VtPHGjgcCCP5SE2blO35W28FlwT1JJpRlFboupCbb5WZlFFFZGwUUUUAFFFFABRRRQAUUUUAdX8O/wDUeKv+xcvP5LXndeifDv8A1Hir/sXLz+S153XTV/gw+f5nHh/95q/9u/kFeg63/wAku8Ff9v8A/wCjxXn1eg63/wAku8Ff9v8A/wCjxRQ+Cp6f+3RDF/xaP+J/+kTOXooormOwKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA6v4d/wCo8Vf9i5efyWvO69E+Hf8AqPFX/YuXn8lrzuumr/Bh8/zOPD/7zV/7d/IK9B1v/kl3gr/t/wD/AEeK8+r0HW/+SXeCv+3/AP8AR4oofBU9P/bohi/4tH/E/wD0iZy9FFFcx2BRRRQAUUUUAFFFFABXRa/oui6QbW3k1fUJbyW1tLqVF09BGizwxzEK/nZYqsmOVGSO1c7XZ6x4ys9WttMt7+z1uW2s4rOGSz/tn/RZFgiSNtsflfIXVCc5O0sTzQMqap4VgVNOGjX9xdzXdu91LHeQR2gt4cgI7uZWUBucbivGw87xVSLwj4gluZbZbJBKjhFVrmJfOZlDKsWW/ekqykBN2Qy46jOzH43trbxBfatYWOrWz6jA9vdlNUVZFQtG6CF0hXygpjUYww2/LgCrVv8AEy9jaYmPVQouvtNv5Wsyoxbyo4sTtjdMMRRngpzuxgHAWoHM+GNIs9Ti1a5v76ezttNshdO0FsJnfM8UIUKXQdZgc57Ve1nwTqtqzz6eo1Gx2wvFIhRZXWXYFzDuLjDyLG2AQHyuSaXwn4xvdGa8F1catcJPp4sYGttRMEtqomil/duVfaP3W0qAOGNdNc/FuZ2e6i0d11ApbJ573gZZWguIZklmXywZJSIFRn3AEcgDnJqBy8PgndfH8V3Qx2RxOHudx/C5ijAztlatJdS9W4s2f7RJG5raXb+X7goZ8VvJ7OAr9u+j2YBz3pMqiI0U2xHvJHGDdOdo+MyaAo3Dyl5E3syK9E7+Ka2sPcyH5iW0tn6Y0ZX0t7I2yWdr6Dce0MkrgOm3z5hP4/kQdXJ1wV3sXfU3ysFx7K0OBn3d8VV+oVn7j6inrY8D9dw4m4S1ldF3+6SNGp1Dl+5i3o/ZmraV+Rj61xA8QG2B69WAJjGmyrR/""")


USER_LOGO_B64 = ""


def decode_base64_jpeg(data: str) -> Image.Image:
    img_bytes = base64.b64decode(data)
    return Image.open(io.BytesIO(img_bytes)).convert("RGBA")


def exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_asset_path(name: str) -> Path:
    bundle_dir = Path(getattr(sys, "_MEIPASS", exe_dir()))
    return bundle_dir / name


def job_file_path(base_dir: Path | None = None) -> Path:
    target_dir = Path(base_dir) if base_dir is not None else exe_dir()
    return target_dir / "ezee_backup_jobs.json"


# --- JOB file integrity ----------------------------------------------------
# Every save writes the JOB file atomically, verifies it, then writes an
# identical safety copy beside it. Every load checks the main file and falls
# back to the safety copy if the main file is missing or corrupted. Each event
# is recorded (with size, job count and SHA-256) in an integrity log, so any
# copy can later be checked against the last known-good fingerprint.
# Between saves, the JOB file and its safety copy are kept read-only: a save
# switches read-only off, writes, then switches it straight back on.
# Dated older copies are kept in a history folder, so an earlier version can be
# recovered after a save that was valid but wrong (e.g. jobs deleted by mistake).

INTEGRITY_LOG_MAX_BYTES = 512 * 1024
HISTORY_KEEP_RECENT = 20  # Always keep this many of the newest dated copies...
HISTORY_KEEP_DAYS = 30  # ...plus the newest copy from each day within this many days
HISTORY_STAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
INTEGRITY_LOG_HEADER = (
    "# EZee-Backup JOB file integrity log\n"
    "# Each line: timestamp | event | file | details (size, jobs, groups, sha256).\n"
    "# To check a copy, compare its SHA-256 with the latest 'SAVE OK' or 'LOAD OK' line, e.g. in PowerShell:\n"
    "#   Get-FileHash 'ezee_backup_jobs.safety.json' -Algorithm SHA256\n"
)


def safety_copy_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.safety{path.suffix}")


def appdata_copy_path(path: Path) -> Path | None:
    """Second safety copy, outside the app folder: %APPDATA%\\EZee-Backup\\<folder>-<id>\\.

    Each app folder gets its own sub-folder (keyed by its full path), so separate
    installs never share or overwrite each other's copies.
    """
    base = os.environ.get("APPDATA")
    if not base:
        return None
    folder = Path(path).resolve().parent
    key = hashlib.sha256(str(folder).lower().encode("utf-8")).hexdigest()[:8]
    label = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in (folder.name or "drive")).strip() or "drive"
    return Path(base) / APP_NAME / f"{label}-{key}" / safety_copy_path(Path(path)).name


def safety_copies(path: Path) -> list[tuple[str, str, Path]]:
    """(description, log event prefix, path) for each safety copy of a JOB file."""
    copies = [("safety copy", "SAFETY", safety_copy_path(path))]
    second = appdata_copy_path(path)
    if second is not None:
        copies.append(("AppData safety copy", "APPDATA", second))
    return copies


def integrity_log_path(path: Path) -> Path:
    """Integrity log for a JOB file. A safety copy shares its main file's log."""
    stem = path.stem.removesuffix(".safety")
    return path.with_name(f"{stem}_integrity.log")


def log_integrity_event(path: Path, event: str, details: str = "", subject: Path | None = None) -> None:
    """Append one line to the integrity log beside `path`. Never raises: logging must not break saving or loading.

    `subject` is the file the event is about, when that is not `path` itself (shown in full if it lives elsewhere).
    """
    log_path = integrity_log_path(path)
    if subject is None:
        file_label = path.name
    else:
        file_label = subject.name if subject.parent == path.parent else str(subject)
    try:
        if log_path.exists() and log_path.stat().st_size > INTEGRITY_LOG_MAX_BYTES:
            os.replace(log_path, log_path.with_name(log_path.name + ".1"))
        is_new = not log_path.exists()
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as handle:
            if is_new:
                handle.write(INTEGRITY_LOG_HEADER)
            parts = [stamp, f"{event:<15}", file_label] + ([details] if details else [])
            handle.write(" | ".join(parts) + "\n")
    except OSError:
        pass


def parse_jobs_document(raw: bytes) -> list:
    """Return the job list from a JOB file's bytes, or raise ValueError describing what is wrong."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"not valid JSON ({exc})") from None
    if isinstance(data, list):
        jobs = data
    elif isinstance(data, dict) and isinstance(data.get("jobs"), list):
        jobs = data["jobs"]
    else:
        raise ValueError("no 'jobs' list found")
    if not all(isinstance(job, dict) for job in jobs):
        raise ValueError("'jobs' contains entries that are not job profiles")
    return jobs


def describe_jobs_file(raw: bytes, jobs: list) -> str:
    groups = {str(job.get("group", "")).strip() for job in jobs} - {""}
    sha = hashlib.sha256(raw).hexdigest()
    return f"size={len(raw)} bytes | jobs={len(jobs)} | groups={len(groups)} | sha256={sha}"


def read_jobs_file(path: Path) -> tuple[list | None, bytes | None, str]:
    """Read and validate a JOB file. Returns (jobs, raw_bytes, problem); jobs is None if unusable."""
    if not path.exists():
        return None, None, "missing"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, None, f"unreadable ({exc})"
    try:
        return parse_jobs_document(raw), raw, ""
    except ValueError as exc:
        return None, raw, f"corrupted: {exc}"


def is_read_only(path: Path) -> bool:
    return not (path.stat().st_mode & stat.S_IWRITE)


def set_read_only(path: Path, read_only: bool) -> None:
    os.chmod(path, stat.S_IREAD if read_only else stat.S_IREAD | stat.S_IWRITE)


def protect_file(path: Path, log_beside: Path | None = None) -> None:
    """Switch read-only on for a JOB file, logging if it had been switched off. Never raises."""
    log_target = log_beside or path
    try:
        if path.exists() and not is_read_only(path):
            set_read_only(path, True)
            log_integrity_event(log_target, "PROTECTED", "read-only switched back on", subject=path)
    except OSError as exc:
        log_integrity_event(log_target, "PROTECT FAILED", f"could not switch on read-only ({exc})", subject=path)


def write_file_atomically(path: Path, raw: bytes, log_beside: Path | None = None) -> None:
    """Write to a temp file in the same folder, flush to disk, then swap it into place.

    The finished file is left read-only. If the existing file is read-only, that is
    switched off just for the swap (and restored if the swap fails).
    """
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    unlocked = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists() and is_read_only(path):
            try:
                set_read_only(path, False)
            except OSError as exc:
                raise OSError(f"could not switch off read-only on {path.name} ({exc})") from exc
            unlocked = True
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.remove(temp_name)
        except OSError:
            pass
        if unlocked:
            try:
                set_read_only(path, True)  # Put the old file's protection back
            except OSError:
                pass
        raise
    try:
        set_read_only(path, True)
    except OSError as exc:
        log_integrity_event(log_beside or path, "PROTECT FAILED", f"saved, but could not switch on read-only ({exc})", subject=path)


def write_safety_copy(target: Path, copy: Path, prefix: str, raw: bytes, event: str, details: str) -> bool:
    """Write and verify one safety copy of the JOB file. Logs the outcome; never raises."""
    try:
        copy.parent.mkdir(parents=True, exist_ok=True)
        write_file_atomically(copy, raw, log_beside=target)
        if copy.read_bytes() != raw:
            raise OSError("did not read back identically after writing")
        if copy.parent != target.parent:
            # Note which app folder this copy belongs to, for anyone browsing %APPDATA%.
            (copy.parent / "copy_of.txt").write_text(
                f"Safety copy of the EZee-Backup JOB file:\n{target.resolve()}\n", encoding="utf-8"
            )
    except OSError as exc:
        log_integrity_event(target, f"{prefix} FAILED", str(exc), subject=copy)
        return False
    log_integrity_event(target, f"{prefix} {event}", details, subject=copy)
    return True


def refresh_safety_copies(target: Path, raw: bytes, jobs: list) -> None:
    """Bring every safety copy in line with a known-good JOB file, then make sure all are read-only."""
    for _label, prefix, copy in safety_copies(target):
        copy_jobs, copy_raw, copy_problem = read_jobs_file(copy)
        if not jobs and copy_jobs:
            # An empty main file must not wipe out a safety copy that still holds profiles.
            log_integrity_event(
                target, f"{prefix} KEPT",
                f"main file has no jobs; copy left untouched | {describe_jobs_file(copy_raw, copy_jobs)}",
                subject=copy,
            )
        elif copy_raw != raw:
            reason = copy_problem or "differs from main file"
            write_safety_copy(target, copy, prefix, raw, "REFRESH", f"was {reason} | {describe_jobs_file(raw, jobs)}")
        protect_file(copy, log_beside=target)
    # Re-apply read-only if it was cleared (crash mid-save, manual change, or older files).
    protect_file(target)


def history_dir(path: Path) -> Path:
    """Folder for dated copies: beside the AppData safety copy, or beside the JOB file if AppData is unavailable."""
    second = appdata_copy_path(path)
    if second is not None:
        return second.parent / "history"
    return path.with_name(f"{path.stem}_history")


def history_files(path: Path) -> list[tuple[datetime, Path]]:
    """Dated copies of a JOB file, newest first."""
    folder = history_dir(path)
    if not folder.is_dir():
        return []
    pattern = re.compile(rf"^{re.escape(path.stem)}_(\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}})(?:_(\d+))?{re.escape(path.suffix)}$")
    found = []
    for candidate in folder.iterdir():
        match = pattern.match(candidate.name)
        if match:
            stamp = datetime.strptime(match.group(1), HISTORY_STAMP_FORMAT)
            found.append((stamp, int(match.group(2) or 0), candidate))
    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [(stamp, candidate) for stamp, _n, candidate in found]


def save_history_copy(target: Path, raw: bytes, jobs: list, now: datetime | None = None) -> None:
    """Add a dated copy of the JOB file (unless the newest one is identical), then prune old ones. Never raises."""
    now = now or datetime.now()
    try:
        existing = history_files(target)
        if existing and existing[0][1].read_bytes() == raw:
            return
        folder = history_dir(target)
        folder.mkdir(parents=True, exist_ok=True)
        base = f"{target.stem}_{now.strftime(HISTORY_STAMP_FORMAT)}"
        copy = folder / f"{base}{target.suffix}"
        counter = 1
        while copy.exists():  # More than one save in the same second
            counter += 1
            copy = folder / f"{base}_{counter}{target.suffix}"
        write_file_atomically(copy, raw, log_beside=target)
    except OSError as exc:
        log_integrity_event(target, "HISTORY FAILED", str(exc), subject=history_dir(target))
        return
    log_integrity_event(target, "HISTORY OK", describe_jobs_file(raw, jobs), subject=copy)
    prune_history(target, now)


def summarize_job_changes(current_jobs: list, older_jobs: list) -> str:
    """Plain-English summary of what restoring `older_jobs` would change, compared with `current_jobs`."""
    current = {str(job.get("name", "Untitled")): job for job in current_jobs}
    older = {str(job.get("name", "Untitled")): job for job in older_jobs}
    brings_back = [name for name in older if name not in current]
    removes = [name for name in current if name not in older]
    changed = [name for name in older if name in current and older[name] != current[name]]

    def listed(names):
        shown = ", ".join(names[:3])
        return shown + (f" +{len(names) - 3} more" if len(names) > 3 else "")

    parts = []
    if brings_back:
        parts.append(f"Brings back: {listed(brings_back)}")
    if removes:
        parts.append(f"Removes: {listed(removes)}")
    if changed:
        parts.append(f"Changes {len(changed)} job{'s' if len(changed) != 1 else ''}")
    return " | ".join(parts) if parts else "Same jobs as now (order or groups may differ)"


def replace_jobs_from_file(target: Path, source: Path, event: str, description: str) -> list:
    """Make another JOB file's contents the current JOB file.

    The current version is kept as a dated copy first, so the change can be undone with Restore Older
    Version. The new contents are saved like any other change (safety copies, dated copy, read-only).
    Returns the new jobs. Raises ValueError if `source` is unusable, OSError if saving fails.
    """
    new_jobs, new_raw, problem = read_jobs_file(source)
    if new_jobs is None:
        raise ValueError(f"{source.name} is {problem}.")
    current_jobs, current_raw, _problem = read_jobs_file(target)
    if current_jobs is not None:
        save_history_copy(target, current_raw, current_jobs)  # No-op if the newest dated copy already matches
    for job in new_jobs:
        job.setdefault("include_subfolders", True)
    save_jobs(new_jobs, target)
    log_integrity_event(target, event, f"from {description} | {describe_jobs_file(new_raw, new_jobs)}")
    return new_jobs


def restore_history_copy(target: Path, dated: Path) -> list:
    """Make a dated copy the current JOB file (Edit > Restore Master Jobs Profile from History)."""
    return replace_jobs_from_file(target, dated, "RESTORED", f"dated copy {dated.name}")


def import_job_file(target: Path, source: Path) -> list:
    """Make a JOB file from anywhere, under any name, the current JOB file (File > Import Master Jobs Profile)."""
    return replace_jobs_from_file(target, Path(source), "IMPORTED", str(Path(source).resolve()))


def prune_history(target: Path, now: datetime | None = None) -> None:
    """Keep the newest HISTORY_KEEP_RECENT copies plus the newest copy of each day in the last HISTORY_KEEP_DAYS days."""
    now = now or datetime.now()
    files = history_files(target)
    keep = {copy for _stamp, copy in files[:HISTORY_KEEP_RECENT]}
    cutoff = now - timedelta(days=HISTORY_KEEP_DAYS)
    days_kept = set()
    for stamp, copy in files:  # Newest first, so the first copy seen for each day is that day's newest
        if stamp >= cutoff and stamp.date() not in days_kept:
            keep.add(copy)
            days_kept.add(stamp.date())
    removed = 0
    for _stamp, copy in files:
        if copy in keep:
            continue
        try:
            set_read_only(copy, False)
            copy.unlink()
            removed += 1
        except OSError as exc:
            log_integrity_event(target, "HISTORY FAILED", f"could not remove old copy ({exc})", subject=copy)
    if removed:
        log_integrity_event(target, "HISTORY PRUNED", f"removed {removed} old dated cop{'y' if removed == 1 else 'ies'}")


def quarantine_corrupt_file(path: Path) -> Path | None:
    """Keep a damaged JOB file for inspection instead of overwriting it. Returns where it was moved."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
    try:
        os.replace(path, destination)
        return destination
    except OSError:
        return None


def load_jobs_with_report(path: str | Path | None = None) -> tuple[list, str | None]:
    """Load the JOB file, recovering from a safety copy if needed.

    Safety copies are tried in order: the one beside the JOB file, then the one in %APPDATA%.
    Returns (jobs, notice). notice is None when all is well, otherwise a message for the user.
    """
    target = Path(path) if path is not None else job_file_path()
    notice = None

    jobs, raw, problem = read_jobs_file(target)
    if jobs is not None:
        log_integrity_event(target, "LOAD OK", describe_jobs_file(raw, jobs))
        refresh_safety_copies(target, raw, jobs)
        save_history_copy(target, raw, jobs)  # No-op if the newest dated copy already matches
    else:
        copies = [(label, prefix, copy, *read_jobs_file(copy)) for label, prefix, copy in safety_copies(target)]
        if (
            problem == "missing"
            and all(copy_problem == "missing" for *_, copy_problem in copies)
            and not history_files(target)
        ):
            log_integrity_event(target, "NO FILE", "no JOB file or safety copies yet (first run)")
            return [], None

        log_integrity_event(target, "LOAD FAILED", problem)
        kept = quarantine_corrupt_file(target) if raw is not None else None
        if kept:
            log_integrity_event(target, "QUARANTINED", f"damaged file kept as {kept.name}")

        # Keep any damaged safety copies for inspection before they are rebuilt.
        for _label, _prefix, copy, copy_jobs, copy_raw, _problem in copies:
            if copy_jobs is None and copy_raw is not None:
                kept_copy = quarantine_corrupt_file(copy)
                if kept_copy:
                    log_integrity_event(target, "QUARANTINED", f"damaged file kept as {kept_copy.name}", subject=copy)

        usable = next((entry for entry in copies if entry[3] is not None), None)
        if usable is None:
            # Last resort: the newest dated copy that is still valid.
            for stamp, dated in history_files(target):
                dated_jobs, dated_raw, dated_problem = read_jobs_file(dated)
                if dated_jobs is not None:
                    label = f"dated copy from {stamp.strftime('%d %B %Y at %H:%M:%S')}"
                    usable = (label, "HISTORY", dated, dated_jobs, dated_raw, "")
                    break
        if usable is None:
            for label, _prefix, copy, _jobs, _raw, copy_problem in copies:
                log_integrity_event(target, "NO RECOVERY", f"{label} {copy_problem}", subject=copy)
            states = "; ".join(f"{label} {copy_problem}" for label, *_, copy_problem in copies)
            notice = (
                f"The JOB file is {problem}, and no usable safety copy or dated copy was found "
                f"({states}).\n\nStarting with an empty job list."
            )
            if kept:
                notice += f"\n\nThe damaged file was kept as:\n{kept}"
            return [], notice

        label, _prefix, source_copy, jobs, recovered_raw, _problem = usable
        try:
            write_file_atomically(target, recovered_raw)
            log_integrity_event(
                target, "RECOVERED",
                f"restored from {label} {source_copy} | {describe_jobs_file(recovered_raw, jobs)}",
            )
            refresh_safety_copies(target, recovered_raw, jobs)
        except OSError as exc:
            log_integrity_event(target, "RESTORE FAILED", f"loaded {label} but could not rewrite main file ({exc})")
        notice = (
            f"The JOB file was {problem}.\n\n"
            f"Your {len(jobs)} job profile(s) were recovered from the {label}:\n{source_copy}"
        )
        if kept:
            notice += f"\n\nThe damaged file was kept as:\n{kept}"

    migrated = False
    for job in jobs:
        if "include_subfolders" not in job:
            job["include_subfolders"] = True
            migrated = True
    if migrated:
        try:
            save_jobs(jobs, target)
        except OSError:
            pass
    return jobs, notice


def load_jobs(path: str | Path | None = None) -> list:
    return load_jobs_with_report(path)[0]


def save_jobs(jobs: list, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else job_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    groups = {}
    for job in jobs:
        group = str(job.get("group", "")).strip()
        if group:
            groups.setdefault(group, []).append(job.get("name", "Untitled"))
    data = {"version": 2, "groups": groups, "jobs": jobs}
    raw = json.dumps(data, indent=2).encode("utf-8")
    try:
        parse_jobs_document(raw)  # Never write something we could not read back
        write_file_atomically(target, raw)
        if target.read_bytes() != raw:
            raise OSError("JOB file did not read back identically after writing")
    except (OSError, ValueError) as exc:
        log_integrity_event(target, "SAVE FAILED", str(exc))
        raise
    details = describe_jobs_file(raw, jobs)
    log_integrity_event(target, "SAVE OK", details)

    # The main file is already safely saved; a failed safety copy is logged rather than failing the save.
    for _label, prefix, copy in safety_copies(target):
        write_safety_copy(target, copy, prefix, raw, "OK", details)
    save_history_copy(target, raw, jobs)
    return target


def build_robocopy_command(source: str, destination: str, mode: str, verbose: bool = False, include_subfolders: bool = True):
    source_norm = str(source).strip().rstrip('\\/')
    dest_norm = str(destination).strip().rstrip('\\/')
    mode_name = (mode or "backup").lower()

    options = ["/R:2", "/W:2", "/COPY:DAT", "/FFT", "/DST"]
    if mode_name == "sync":
        options = ["/MIR", "/R:2", "/W:2", "/COPY:DAT", "/FFT", "/DST"]
    elif mode_name in {"move", "transfer"}:
        options = (["/E"] if include_subfolders else []) + ["/MOV", "/COPY:DAT", "/FFT", "/DST", "/R:2", "/W:2"]
    elif mode_name == "compare":
        options = ["/L"] + (["/E"] if include_subfolders else []) + ["/COPY:DAT", "/FFT", "/DST", "/R:2", "/W:2"]
    else:
        options = (["/E"] if include_subfolders else []) + ["/COPY:DAT", "/FFT", "/DST", "/R:2", "/W:2"]

    if verbose:
        options.append("/V")

    command = ["robocopy", source_norm, dest_norm, *options]
    return command


def has_valid_folder_pair(source: str, destination: str) -> bool:
    return bool(str(source).strip()) and bool(str(destination).strip())


def extract_drive_letter(path: str) -> str | None:
    candidate = str(path).strip()
    if len(candidate) >= 2 and candidate[1] == ":" and candidate[0].isalpha():
        return candidate[:2].upper()
    return None


def collect_drive_letters(jobs: list) -> set:
    drives = set()
    for job in jobs:
        for key in ("source", "destination"):
            drive = extract_drive_letter(job.get(key, ""))
            if drive:
                drives.add(drive)
    return drives


def is_drive_online(drive_letter: str) -> bool:
    return os.path.exists(f"{drive_letter}\\")


# --- Windows WM_DEVICECHANGE plumbing -------------------------------------
# Lets the app learn about a drive arriving/departing the instant Windows
# broadcasts it, instead of relying solely on the periodic poll.

WM_DEVICECHANGE = 0x0219
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVTYP_VOLUME = 2
GWLP_WNDPROC = -4

WNDPROCTYPE = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
)

_user32 = ctypes.windll.user32
_user32.SetWindowLongPtrW.restype = ctypes.c_void_p
_user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_user32.CallWindowProcW.restype = ctypes.c_ssize_t
_user32.CallWindowProcW.argtypes = [
    ctypes.c_void_p, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM,
]


class DEV_BROADCAST_HDR(ctypes.Structure):
    _fields_ = [
        ("dbch_size", wintypes.DWORD),
        ("dbch_devicetype", wintypes.DWORD),
        ("dbch_reserved", wintypes.DWORD),
    ]


class DEV_BROADCAST_VOLUME(ctypes.Structure):
    _fields_ = [
        ("dbcv_size", wintypes.DWORD),
        ("dbcv_devicetype", wintypes.DWORD),
        ("dbcv_reserved", wintypes.DWORD),
        ("dbcv_unitmask", wintypes.DWORD),
        ("dbcv_flags", wintypes.WORD),
    ]


def unitmask_to_drive_letters(unitmask: int) -> list:
    return [f"{chr(ord('A') + i)}:" for i in range(26) if unitmask & (1 << i)]


def paths_are_accessible(source: str, destination: str) -> tuple[bool, str]:
    source = str(source).strip()
    destination = str(destination).strip()
    source_drive = extract_drive_letter(source)
    if source_drive and not is_drive_online(source_drive):
        return False, f"Source drive {source_drive} is offline or disconnected."
    if not os.path.isdir(source):
        return False, f"Source folder is not accessible: {source}"
    dest_drive = extract_drive_letter(destination)
    if dest_drive and not is_drive_online(dest_drive):
        return False, f"Destination drive {dest_drive} is offline or disconnected."
    return True, ""


def folder_dialog_initialdir(folder: str) -> str | None:
    """Folder the Browse dialog should open at: the text-box path, or its nearest existing parent."""
    candidate = str(folder).strip().strip('"')
    if not candidate:
        return None
    candidate = os.path.normpath(candidate)
    while not os.path.isdir(candidate):
        parent = os.path.dirname(candidate)
        if not parent or parent == candidate:
            return None  # Nothing on this path exists (e.g. drive not connected)
        candidate = parent
    return candidate


def icon_key_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
        return "image"
    if suffix in {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}:
        return "video"
    if suffix in {".zip", ".7z", ".rar", ".tar", ".gz"}:
        return "archive"
    if suffix in {".exe", ".msi", ".bat", ".cmd", ".ps1"}:
        return "application"
    return "file"


def is_successful_robocopy_exit_code(code: int) -> bool:
    return 0 <= code <= 7


def play_completion_chime():
    if winsound is None:
        return

    def chime():
        try:
            sound_path = bundled_asset_path("EZ-guitar.wav")
            if sound_path.exists():
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound("Tada", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except (RuntimeError, OSError):
            try:
                winsound.PlaySound("Tada", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except (RuntimeError, OSError):
                pass

    threading.Thread(target=chime, daemon=True).start()


def play_error_sound():
    if winsound is None:
        return

    def sound():
        try:
            sound_path = bundled_asset_path("EZ-error.wav")
            if sound_path.exists():
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except (RuntimeError, OSError):
            try:
                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except (RuntimeError, OSError):
                pass

    threading.Thread(target=sound, daemon=True).start()


def play_standard_alert_beep():
    """Lighter nudge than play_error_sound(), used as a repeat reminder
    rather than a fresh-event alert."""
    if winsound is None:
        return

    def beep():
        try:
            sound_path = bundled_asset_path("EZ-short-alert1.wav")
            if sound_path.exists():
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.MessageBeep(winsound.MB_ICONHAND)
        except (RuntimeError, OSError):
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except (RuntimeError, OSError):
                pass

    threading.Thread(target=beep, daemon=True).start()


def jobs_for_sidebar_selection(jobs: list, kind: str, value: str) -> list:
    if kind == "job":
        return [jobs[int(value)]]
    if kind == "group":
        return [job for job in jobs if str(job.get("group", "")).strip() == value]
    return []


# --- Two-way Sync mode -----------------------------------------------------
# Robocopy has no bidirectional mode, so Sync is implemented as a custom
# Python engine that remembers each folder pair's state from the last
# successful sync (a "manifest") so it can tell a genuine deletion apart
# from a file that simply hasn't reached the other side yet.

def sync_state_dir(base_dir: Path | None = None) -> Path:
    target_dir = Path(base_dir) if base_dir is not None else exe_dir()
    return target_dir / "sync_state"


def sync_pair_key(source: str, destination: str) -> str:
    def normalize(path: str) -> str:
        return os.path.normcase(os.path.normpath(str(path).strip()))

    digest = hashlib.sha1(f"{normalize(source)}|{normalize(destination)}".encode("utf-8"))
    return digest.hexdigest()


def sync_manifest_path(source: str, destination: str, base_dir: Path | None = None) -> Path:
    return sync_state_dir(base_dir) / f"{sync_pair_key(source, destination)}.json"


def load_sync_manifest(source: str, destination: str, base_dir: Path | None = None) -> dict:
    target = sync_manifest_path(source, destination, base_dir)
    if not target.exists():
        return {}
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        entries = data.get("entries")
        return entries if isinstance(entries, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_sync_manifest(source: str, destination: str, entries: dict, base_dir: Path | None = None) -> Path:
    target = sync_manifest_path(source, destination, base_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "source": str(source),
        "destination": str(destination),
        "generated": date.today().isoformat(),
        "entries": entries,
    }
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return target


def scan_folder_snapshot(root: Path, include_subfolders: bool) -> dict:
    root = Path(root)
    snapshot = {}
    if not root.exists():
        return snapshot
    if include_subfolders:
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                full_path = Path(dirpath) / filename
                try:
                    stat = full_path.stat()
                except OSError:
                    continue
                relative = full_path.relative_to(root).as_posix()
                snapshot[relative] = (stat.st_size, stat.st_mtime)
    else:
        try:
            entries = os.scandir(root)
        except OSError:
            return snapshot
        with entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    continue
                try:
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                snapshot[entry.name] = (stat.st_size, stat.st_mtime)
    return snapshot


def classify_sync_entries(
    source_entries: dict,
    dest_entries: dict,
    manifest_entries: dict,
    mtime_tolerance: float = 2.0,
) -> dict:
    def sizes_and_times_match(a, b) -> bool:
        return a[0] == b[0] and abs(a[1] - b[1]) <= mtime_tolerance

    actions = {}
    all_paths = set(source_entries) | set(dest_entries) | set(manifest_entries)
    for relative_path in all_paths:
        in_source = relative_path in source_entries
        in_dest = relative_path in dest_entries
        in_manifest = relative_path in manifest_entries

        if not in_manifest:
            if in_source and in_dest:
                if sizes_and_times_match(source_entries[relative_path], dest_entries[relative_path]):
                    actions[relative_path] = "noop"
                else:
                    actions[relative_path] = "conflict"
            elif in_source:
                actions[relative_path] = "copy_src_to_dest"
            elif in_dest:
                actions[relative_path] = "copy_dest_to_src"
            continue

        if not in_source and not in_dest:
            actions[relative_path] = "noop"
            continue
        if in_source and not in_dest:
            actions[relative_path] = "delete_src"
            continue
        if in_dest and not in_source:
            actions[relative_path] = "delete_dest"
            continue

        manifest_value = manifest_entries[relative_path]
        manifest_tuple = (manifest_value[0], manifest_value[1]) if isinstance(manifest_value, (list, tuple)) else (manifest_value.get("size"), manifest_value.get("mtime"))
        source_changed = not sizes_and_times_match(source_entries[relative_path], manifest_tuple)
        dest_changed = not sizes_and_times_match(dest_entries[relative_path], manifest_tuple)

        if source_changed and dest_changed:
            actions[relative_path] = "conflict"
        elif source_changed:
            actions[relative_path] = "copy_src_to_dest"
        elif dest_changed:
            actions[relative_path] = "copy_dest_to_src"
        else:
            actions[relative_path] = "noop"

    return actions


@dataclass
class SyncResult:
    success: bool = True
    aborted: bool = False
    copied_to_dest: int = 0
    copied_to_source: int = 0
    deleted_from_dest: int = 0
    deleted_from_source: int = 0
    conflicts: int = 0
    errors: list = field(default_factory=list)
    conflict_details: list = field(default_factory=list)


def _conflict_copy_path(path: Path, label: str) -> Path:
    return path.with_name(f"{path.stem} (Sync Conflict - {label}){path.suffix}")


def run_sync_engine(
    source: str,
    destination: str,
    include_subfolders: bool,
    pause_event: threading.Event,
    abort_event: threading.Event,
    log_queue: queue.Queue,
    base_dir: Path | None = None,
) -> SyncResult:
    source_root = Path(source)
    dest_root = Path(destination)
    result = SyncResult()

    manifest_entries = load_sync_manifest(source, destination, base_dir)
    source_snapshot = scan_folder_snapshot(source_root, include_subfolders)
    dest_snapshot = scan_folder_snapshot(dest_root, include_subfolders)
    actions = classify_sync_entries(source_snapshot, dest_snapshot, manifest_entries)

    conflict_label = date.today().isoformat()
    aborted = False

    for relative_path, action in sorted(actions.items()):
        if abort_event.is_set():
            aborted = True
            break
        pause_event.wait()
        if abort_event.is_set():
            aborted = True
            break

        source_path = source_root / relative_path
        dest_path = dest_root / relative_path

        try:
            if action == "noop":
                continue
            elif action == "copy_src_to_dest":
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)
                result.copied_to_dest += 1
                log_queue.put(f"Sync: copied {relative_path} -> Destination")
            elif action == "copy_dest_to_src":
                source_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest_path, source_path)
                result.copied_to_source += 1
                log_queue.put(f"Sync: copied {relative_path} -> Source")
            elif action == "delete_dest":
                if dest_path.exists():
                    if send2trash is not None:
                        send2trash(str(dest_path))
                    else:
                        dest_path.unlink()
                result.deleted_from_dest += 1
                log_queue.put(f"Sync: removed {relative_path} from Destination (deleted on Source)")
            elif action == "delete_src":
                if source_path.exists():
                    if send2trash is not None:
                        send2trash(str(source_path))
                    else:
                        source_path.unlink()
                result.deleted_from_source += 1
                log_queue.put(f"Sync: removed {relative_path} from Source (deleted on Destination)")
            elif action == "conflict":
                source_newer = source_path.stat().st_mtime >= dest_path.stat().st_mtime
                winner_path, loser_path = (source_path, dest_path) if source_newer else (dest_path, source_path)
                loser_conflict_dest = _conflict_copy_path(dest_path, conflict_label)
                loser_conflict_source = _conflict_copy_path(source_path, conflict_label)

                # Preserve the loser's bytes under conflict-marked names on BOTH
                # sides before anything gets overwritten with the winner's content.
                shutil.copy2(loser_path, loser_conflict_dest)
                shutil.copy2(loser_path, loser_conflict_source)

                if winner_path != dest_path:
                    shutil.copy2(winner_path, dest_path)
                if winner_path != source_path:
                    shutil.copy2(winner_path, source_path)

                result.conflicts += 1
                winner_label = "Source" if winner_path == source_path else "Destination"
                detail = (
                    f"{relative_path}\n"
                    f"    Newer version kept (from {winner_label})\n"
                    f"    Older version saved as: {loser_conflict_dest.name}"
                )
                result.conflict_details.append(detail)
                log_queue.put(
                    f"Sync: CONFLICT on {relative_path} - kept newer version, "
                    f"older version saved as {loser_conflict_dest.name}"
                )
        except OSError as exc:
            result.errors.append(f"{relative_path}: {exc}")
            log_queue.put(f"Sync ERROR on {relative_path}: {exc}")

    result.aborted = aborted
    result.success = not aborted and not result.errors

    if not aborted:
        final_source_snapshot = scan_folder_snapshot(source_root, include_subfolders)
        final_manifest = {
            path: {"size": size, "mtime": mtime}
            for path, (size, mtime) in final_source_snapshot.items()
        }
        save_sync_manifest(source, destination, final_manifest, base_dir)

    return result


class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._hide()
        self.after_id = self.widget.after(500, self._show)

    def _show(self):
        if self.tip_window is not None or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip_window,
            text=self.text,
            bg="#0f172a",
            fg="#e2e8f0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=3,
        ).pack()

    def _hide(self, _event=None):
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}


def new_folder_name_problem(name: str) -> str | None:
    """Return why name can't be used for a new Windows folder, or None if it's fine."""
    if not name:
        return "Please enter a folder name."
    if any(ch in '<>:"/\\|?*' or ord(ch) < 32 for ch in name):
        return "A folder name can't contain any of these characters:\n" + '< > : " / \\ | ? *'
    if name.endswith((".", " ")):
        return "A folder name can't end with a full stop or a space."
    if name.split(".")[0].upper() in WINDOWS_RESERVED_NAMES:
        return f"'{name}' is a name reserved by Windows."
    return None


class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"{APP_NAME} - Welcome")
        self.configure(bg="#0b1020")
        self.geometry("460x690")
        self.resizable(False, False)
        self.transient(parent)
        self.attributes("-topmost", True)

        try:
            if USER_LOGO_B64:
                payload = decode_base64_jpeg(USER_LOGO_B64)
            else:
                payload = Image.open(bundled_asset_path("EZeeBACK Logo.jpg")).convert("RGBA")
            payload.thumbnail((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(payload)
            self.image = photo
            logo = tk.Label(self, image=photo, bg="#0b1020", borderwidth=0)
            logo.pack(pady=(24, 12))
        except Exception:
            logo = tk.Label(self, text=APP_NAME, font=("Segoe UI", 24, "bold"), bg="#0b1020", fg="#e2e8f0")
            logo.pack(pady=(80, 35))

        tk.Label(self, text=APP_NAME, font=("Segoe UI", 22, "bold"), bg="#0b1020", fg="#e2e8f0").pack()
        tk.Label(self, text=f"Version {VERSION}", font=("Segoe UI", 12), bg="#0b1020", fg="#38bdf8").pack(pady=(2, 16))
        tk.Label(
            self,
            text="Developed by Adrian Newington\nas a Vibe Coding Project\nusing Python and Google Code Assist AI\n\nGithub.com/SunflowerGUY",
            font=("Segoe UI", 10),
            justify="center",
            bg="#0b1020",
            fg="#cbd5e1",
        ).pack()
        coffee_link = add_coffee_link(self)
        coffee_link.configure(bg="#0b1020")
        coffee_link.pack(pady=(14, 0))

        button = tk.Button(
            self,
            text="Click to Start",
            command=self.close,
            bg="#38bdf8",
            fg="#0f172a",
            activebackground="#7dd3fc",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=8,
            pady=8,
        )
        button.pack(pady=(22, 20))

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.update_idletasks()
        parent.update()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2 - 30
        self.geometry(f"+{x}+{y}")

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()


class EZeeBackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Version {VERSION}")
        self.geometry("980x850")
        self.minsize(900, 760)
        self.configure(bg="#0b1020")
        try:
            # default= also gives every pop-up window (About, dialogs, message boxes) the app icon
            self.iconbitmap(default=str(bundled_asset_path("ezee-backup.ico")))
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Import Master Jobs Profile (JSON)...", command=self.import_job_file_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy, accelerator="Ctrl+Q")
        menu_bar.add_cascade(label="File", menu=file_menu, underline=0)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Save as New Job", command=self.save_current_job)
        edit_menu.add_command(label="Delete Job", command=self.delete_current_job)
        edit_menu.add_separator()
        edit_menu.add_command(label="Save Changes", command=self.save_job_changes, accelerator="Ctrl+S", state=tk.DISABLED)
        edit_menu.add_command(label="Forget Changes", command=self.forget_changes, state=tk.DISABLED)
        edit_menu.add_separator()
        edit_menu.add_command(label="Restore Master Jobs Profile from History...", command=self.open_restore_older_version)
        self.edit_menu = edit_menu
        menu_bar.add_cascade(label="Edit", menu=edit_menu, underline=0)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.open_about)
        help_menu.add_command(label="Backup Mode Info", command=self.open_backup_info)
        help_menu.add_separator()
        help_menu.add_command(label=f"Support {APP_NAME} ☕…", command=self.show_coffee)
        menu_bar.add_cascade(label="Help", menu=help_menu, underline=0)

        self.bind_all("<Control-s>", lambda event: self.save_job_changes())
        self.bind_all("<Control-q>", lambda event: self.destroy())

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="backup")
        self.include_subfolders_var = tk.BooleanVar(value=True)
        self.log_mode_var = tk.StringVar(value="Simple")
        self._loading_job = False
        self._profile_modified = False
        self.source_var.trace_add("write", self._profile_field_changed)
        self.destination_var.trace_add("write", self._profile_field_changed)
        self.mode_var.trace_add("write", self._profile_field_changed)
        self.include_subfolders_var.trace_add("write", self._profile_field_changed)
        self.active_process = None
        self.process_paused = False
        self.operation_aborted = False
        self.active_sync_thread = None
        self.sync_pause_event = threading.Event()
        self.sync_pause_event.set()
        self.sync_abort_event = threading.Event()
        self._destination_refresh_scheduled = False
        self.pending_jobs = []
        self.batch_job_names = []
        self.batch_job_results = []
        self.known_drive_status = {}
        self._last_offline_transition = []
        self._last_selection_offline_drives = []

        self.jobs, load_notice = load_jobs_with_report(job_file_path())
        self._build_ui()
        self._center_window()
        if load_notice:
            self.after_idle(lambda: self._report_job_file_recovery(load_notice))
        self._old_wndproc = None
        self._install_drive_change_watcher()
        self.after_idle(self._check_drive_availability)

    def _center_window(self):
        self.update_idletasks()
        width = max(self.winfo_reqwidth(), 980)
        height = max(self.winfo_reqheight(), 850)
        usable_height = max(0, self.winfo_screenheight() - 48)
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (usable_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        self._create_file_icons()
        top = tk.Frame(self, bg="#0b1020", padx=18, pady=2)
        top.pack(fill="x")

        title_row = tk.Frame(top, bg="#0b1020")
        title_row.pack(fill="x")
        try:
            logo_image = Image.open(bundled_asset_path("EZeeBACK Logo.jpg")).convert("RGBA")
            logo_image.thumbnail((34, 34), Image.Resampling.LANCZOS)
            self.title_logo = ImageTk.PhotoImage(logo_image)
            tk.Label(title_row, image=self.title_logo, bg="#0b1020", borderwidth=0).pack(side="left", padx=(0, 8))
        except (OSError, tk.TclError):
            pass
        title = tk.Label(title_row, text=f"{APP_NAME}", font=("Segoe UI", 20, "bold"), fg="#e2e8f0", bg="#0b1020")
        title.pack(side="left")
        subtitle = tk.Label(title_row, text=f"Version {VERSION}", font=("Segoe UI", 9), fg="#7dd3fc", bg="#0b1020")
        subtitle.pack(side="left", padx=(10, 0), pady=(6, 0))
        action_row = tk.Frame(title_row, bg="#0b1020")
        action_row.pack(side="right")
        tk.Button(
            action_row,
            text="About",
            command=self.open_about,
            bg="#1f2937",
            fg="#e2e8f0",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            action_row,
            text="Exit",
            command=self.destroy,
            bg="#7f1d1d",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="left")

        workspace = tk.Frame(self, bg="#0b1020")
        workspace.pack(fill="both", expand=True, padx=18, pady=(2, 4))
        sidebar = tk.LabelFrame(workspace, text="Groups & Jobs", bg="#111827", fg="#e2e8f0", padx=8, pady=4)
        sidebar.configure(width=300)
        sidebar.pack_propagate(False)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar_view = tk.Frame(sidebar, bg="#111827")
        sidebar_view.pack(fill="both", expand=True)
        sidebar_tree_style = ttk.Style(self)
        sidebar_tree_style.configure("Sidebar.Treeview", font=("Segoe UI", 10, "bold"))
        self.job_tree = ttk.Treeview(sidebar_view, style="Sidebar.Treeview", show="tree", selectmode="browse", height=22)
        sidebar_scrollbar = ttk.Scrollbar(sidebar_view, orient="vertical", command=self.job_tree.yview)
        self.job_tree.configure(yscrollcommand=sidebar_scrollbar.set)
        self.job_tree.pack(side="left", fill="both", expand=True)
        sidebar_scrollbar.pack(side="right", fill="y")
        self.job_tree.tag_configure("backup", foreground="#3f8f5f", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("sync", foreground="#ef4444", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("move", foreground="#3b82f6", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("compare", foreground="#a855f7", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("twoway", foreground="#f59e0b", font=("Segoe UI", 10, "bold"))
        self.job_tree.bind("<<TreeviewSelect>>", self._select_sidebar_item)
        self.job_tree.bind("<Button-3>", self._show_job_context_menu)
        form = tk.LabelFrame(workspace, text="Backup Settings", bg="#111827", fg="#e2e8f0", padx=12, pady=4, borderwidth=2, relief="groove")
        form.pack(side="left", fill="both", expand=True)

        self.job_profile_label = tk.Label(
            form,
            text="Showing Job Profile: ",
            anchor="w",
            bg="#111827",
            fg="#ffff00",
            font=("Segoe UI", 11, "bold"),
        )
        self.job_profile_label.pack(fill="x", pady=(0, 3))

        self.drive_warning_label = tk.Label(
            form,
            text="",
            anchor="w",
            bg="#111827",
            fg="#ef4444",
            font=("Segoe UI", 10, "bold"),
        )
        self.drive_warning_label.pack(fill="x", pady=(0, 3))

        row = tk.Frame(form, bg="#111827")
        row.pack(fill="x", pady=3)
        tk.Label(row, text="Source Folder", width=18, anchor="w", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left")
        source_entry = tk.Entry(row, textvariable=self.source_var, width=1, bg="#ffffff", fg="#111827", insertbackground="#111827", relief="solid", borderwidth=1)
        source_entry.pack(side="left", fill="x", expand=True, padx=(8, 10), ipady=3)
        tk.Button(row, text="Browse", command=self.browse_source, bg="#1f2937", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12).pack(side="left")
        self.include_subfolders_checkbutton = tk.Checkbutton(
            row,
            text="Include Sub Folders",
            variable=self.include_subfolders_var,
            bg="#111827",
            fg="#e2e8f0",
            activebackground="#111827",
            activeforeground="#ffffff",
            selectcolor="#0f172a",
            font=("Segoe UI", 10),
            command=self._include_subfolders_changed,
        )
        self.include_subfolders_checkbutton.pack(side="left", padx=(12, 0))

        row2 = tk.Frame(form, bg="#111827")
        row2.pack(fill="x", pady=3)
        tk.Label(row2, text="Destination Folder", width=18, anchor="w", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left")
        destination_entry = tk.Entry(row2, textvariable=self.destination_var, width=1, bg="#ffffff", fg="#111827", insertbackground="#111827", relief="solid", borderwidth=1)
        destination_entry.pack(side="left", fill="x", expand=True, padx=(8, 10), ipady=3)
        tk.Button(row2, text="Browse", command=self.browse_destination, bg="#1f2937", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12).pack(side="left")
        destination_spacer = tk.Frame(row2, width=self.include_subfolders_checkbutton.winfo_reqwidth(), height=1, bg="#111827")
        destination_spacer.pack_propagate(False)
        destination_spacer.pack(side="left", padx=(12, 0))

        jobs_frame = tk.Frame(form, bg="#111827")
        jobs_frame.pack(fill="x", pady=(2, 2))
        job_row = tk.Frame(jobs_frame, bg="#111827")
        job_row.pack(fill="x")
        tk.Label(job_row, text="Job:", bg="#111827", fg="#cbd5e1").pack(side="left", padx=(0, 8))
        self.job_name = tk.StringVar(value="Daily Backup")
        self.job_name.trace_add("write", self._update_job_profile_label)
        self._update_job_profile_label()
        tk.Button(job_row, text="Save as New Job", command=self.save_current_job, bg="#1f2937", fg="#e2e8f0", relief="flat", font=("Segoe UI", 10, "bold"), padx=10).pack(side="left")
        tk.Button(job_row, text="Delete Job", command=self.delete_current_job, bg="#1f2937", fg="#e2e8f0", relief="flat", font=("Segoe UI", 10, "bold"), padx=10).pack(side="left", padx=(8, 0))
        self.save_changes_button = tk.Button(
            job_row,
            text="Save Changes",
            command=self.save_job_changes,
            bg="#1f2937",
            fg="#ffffff",
            activeforeground="#ffffff",
            state=tk.DISABLED,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=10,
        )
        self.save_changes_button.pack(side="left", padx=(8, 0))
        self.forget_changes_button = tk.Button(
            job_row,
            text="Forget Changes",
            command=self.forget_changes,
            bg="#1f2937",
            fg="#ffffff",
            activeforeground="#ffffff",
            state=tk.DISABLED,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=10,
        )
        self.forget_changes_button.pack(side="left", padx=(8, 0))
        self.refresh_jobs_list(collapsed=True)  # Start with every sidebar node closed

        folder_views = tk.Frame(form, bg="#111827")
        folder_views.pack(fill="both", expand=True, pady=(3, 2))
        self.source_tree = self._create_folder_view(folder_views, "Source Folder")
        self.destination_tree = self._create_folder_view(folder_views, "Destination Folder")

        controls = tk.Frame(form, bg="#111827")
        controls.pack(fill="x", pady=3)

        mode_container = tk.LabelFrame(controls, text="", bg="#111827", fg="#e2e8f0", padx=8, pady=6, borderwidth=2, relief="solid")
        mode_container.configure(highlightbackground="#0041a3", highlightcolor="#0041a3", highlightthickness=2)
        mode_container.pack(side="left", fill="y")

        mode_frame = tk.Frame(mode_container, bg="#111827")
        mode_frame.pack(side="left")
        mode_colors = {"backup": "#00ff00", "sync": "#ff3333", "move": "#00c3ff", "compare": "#e400ff", "twoway": "#f59e0b"}
        for label, value in [("Backup", "backup"), ("Mirror", "sync"), ("Move", "move"), ("Compare", "compare"), ("Sync", "twoway")]:
            tk.Radiobutton(
                mode_frame,
                text=label,
                variable=self.mode_var,
                value=value,
                command=self._mode_changed,
                bg="#111827",
                fg=mode_colors[value],
                activeforeground=mode_colors[value],
                selectcolor="#0f172a",
                activebackground="#111827",
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", padx=(0, 16))

        self.backup_info_image = ImageTk.PhotoImage(
            Image.open(bundled_asset_path("backup-info.png")).resize((32, 32), Image.Resampling.LANCZOS)
        )
        backup_info_button = tk.Button(
            mode_frame,
            image=self.backup_info_image,
            command=self.open_backup_info,
            bg="#111827",
            activebackground="#334155",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=2,
            pady=2,
            cursor="hand2",
            takefocus=True,
        )
        backup_info_button.pack(side="left", padx=(0, 4))
        ToolTip(backup_info_button, "Backup Info")

        checks = tk.Frame(controls, bg="#111827")
        checks.pack(side="left", padx=(18, 0), pady=6)
        tk.Label(checks, text="Log:", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 4))
        self.log_mode_selector = ttk.Combobox(checks, textvariable=self.log_mode_var, values=("Simple", "Verbose", "No Logs"), state="readonly", width=10)
        self.log_mode_selector.pack(side="left", padx=(0, 8))

        action_group = tk.Frame(controls, bg="#111827")
        action_group.pack(side="right")
        tk.Button(
            action_group,
            text="Refresh Folders",
            command=self.refresh_folder_views,
            bg="#0060ff",
            fg="#ffffff",
            activebackground="#004ecc",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=8,
            pady=8,
            relief="flat",
            width=14,
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            action_group,
            text="RUN",
            command=self.run_backup,
            bg="#ff3600",
            fg="#ffffff",
            activebackground="#d92d00",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=8,
            pady=8,
            relief="flat",
            width=8,
        )
        self.run_button = action_group.winfo_children()[-1]
        self.run_button.pack(side="left")
        self.pause_button = tk.Button(action_group, text="Pause", command=self.toggle_pause, bg="#5b4a2f", fg="#000000", disabledforeground="#000000", activebackground="#f59e0b", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12, pady=8, state="disabled")
        self.pause_button.pack(side="left", padx=(10, 0))
        self.abort_button = tk.Button(action_group, text="Abort", command=self.abort_operation, bg="#5f3030", fg="#000000", disabledforeground="#000000", activebackground="#ef4444", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12, pady=8, state="disabled")
        self.abort_button.pack(side="left", padx=(8, 0))

        log_frame = tk.LabelFrame(self, text="Activity Log", bg="#111827", fg="#e2e8f0", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        log_view = tk.Frame(log_frame, bg="#020817")
        log_view.pack(fill="both", expand=True)
        self.log_widget = tk.Text(log_view, height=8, bg="#020817", fg="#dbeafe", insertbackground="#e2e8f0", padx=8, pady=8)
        self.log_widget.tag_configure("job_report", foreground="#ffff00")
        log_scrollbar = ttk.Scrollbar(log_view, orient="vertical", command=self.log_widget.yview)
        self.log_widget.configure(yscrollcommand=log_scrollbar.set)
        self.log_widget.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        self.log_widget.insert("end", "EZee-Backup ready.\n")
        self.log_widget.insert("end", "Use Right-Click to copy Log Files.\n", "job_report")
        self.log_widget.see("end")
        self.log_widget.bind("<Button-3>", self._show_log_context_menu)

    def _show_log_context_menu(self, event=None):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy Selected", command=self._copy_selected_log_text)
        menu.add_command(label="Copy Logs", command=self._copy_logs_to_clipboard)
        menu.add_command(label="Copy Logs and Launch NOTEPAD", command=self._copy_logs_and_launch_notepad)
        menu.add_separator()
        menu.add_command(label="Clear Log", command=self._clear_log)
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_selected_log_text(self):
        selected = self.log_widget.get(tk.SEL_FIRST, tk.SEL_LAST) if self.log_widget.tag_ranges(tk.SEL) else ""
        if not selected:
            return
        self.clipboard_clear()
        self.clipboard_append(selected)

    def _copy_logs_to_clipboard(self):
        log_text = self.log_widget.get("1.0", "end").rstrip()
        self.clipboard_clear()
        self.clipboard_append(log_text)

    def _copy_logs_and_launch_notepad(self):
        log_text = self.log_widget.get("1.0", "end").rstrip()
        self.clipboard_clear()
        self.clipboard_append(log_text)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="ezee-backup-logs-",
                encoding="utf-8",
                delete=False,
            ) as log_file:
                log_file.write(log_text)
                log_path = log_file.name
            subprocess.Popen(["notepad.exe", log_path])
        except OSError as exc:
            messagebox.showerror("Notepad", f"Unable to launch Notepad:\n{exc}", parent=self)

    def _clear_log(self):
        self.log_widget.delete("1.0", "end")
        self.log_widget.insert("end", "EZee-Backup ready.\n")
        self.log_widget.see("end")

    def _set_operation_controls(self, running):
        if running:
            self.run_button.configure(state="disabled")
        else:
            self._update_run_button_state()
        self.pause_button.configure(state="normal" if running else "disabled")
        self.abort_button.configure(state="normal" if running else "disabled")
        if running:
            self.pause_button.configure(bg="#b45309", fg="#ffffff")
            self.abort_button.configure(bg="#b91c1c", fg="#ffffff")
        else:
            self.pause_button.configure(bg="#5b4a2f", fg="#000000")
            self.abort_button.configure(bg="#5f3030", fg="#000000")

    def _set_process_paused(self, process, paused):
        if os.name != "nt":
            raise OSError("Process pause is only supported on Windows.")
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x0800, False, process.pid)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            function_name = "NtSuspendProcess" if paused else "NtResumeProcess"
            function = ctypes.WinDLL("ntdll").__getattr__(function_name)
            status = function(handle)
            if status != 0:
                raise OSError(f"Unable to {'pause' if paused else 'resume'} the backup process.")
        finally:
            kernel32.CloseHandle(handle)

    def toggle_pause(self):
        process = self.active_process
        sync_running = self.active_sync_thread is not None and self.active_sync_thread.is_alive()
        if process is not None and process.poll() is None:
            paused = not self.process_paused
            try:
                self._set_process_paused(process, paused)
            except OSError as exc:
                self._log(f"Unable to {'pause' if paused else 'resume'} operation: {exc}")
                return False
        elif sync_running:
            paused = not self.process_paused
            if paused:
                self.sync_pause_event.clear()
            else:
                self.sync_pause_event.set()
        else:
            return False
        self.process_paused = paused
        self.pause_button.configure(text="Resume" if paused else "Pause")
        self._log("Operation paused." if paused else "Operation resumed.")
        return True

    def abort_operation(self):
        process = self.active_process
        sync_running = self.active_sync_thread is not None and self.active_sync_thread.is_alive()
        if process is not None and process.poll() is not None:
            process = None
        if process is None and not sync_running:
            return
        paused_before_abort = self.process_paused
        if not paused_before_abort and not self.toggle_pause():
            return
        if not messagebox.askyesno("Abort operation", "Abort the current backup operation?", parent=self):
            if not paused_before_abort:
                self.toggle_pause()
            return
        self.operation_aborted = True
        if process is not None:
            try:
                process.terminate()
                self._log("Abort requested. Waiting for Robocopy to stop...")
            except OSError as exc:
                self._log(f"Unable to abort operation: {exc}")
        else:
            self.sync_abort_event.set()
            # Wake a currently-paused worker thread so it can reach the abort checkpoint.
            self.sync_pause_event.set()
            self._log("Abort requested. Waiting for Sync to stop...")

    def _create_folder_view(self, parent, title):
        panel = tk.Frame(parent, bg="#111827")
        panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(panel, text=title, anchor="w", bg="#111827", fg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(0, 4))

        view_frame = tk.Frame(panel, bg="#111827")
        view_frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(view_frame, columns=("size",), show="tree headings", height=12)
        tree.heading("#0", text="Name")
        tree.heading("size", text="Size")
        tree.column("#0", anchor="w", width=280, stretch=True)
        tree.column("size", anchor="e", width=100, stretch=False)
        tree._file_icons = self.file_icons
        tree._folder_paths = {}
        tree._loaded_folders = set()
        tree._root_path = None
        tree._include_subfolders = True
        tree.bind("<<TreeviewOpen>>", self._expand_folder_item)
        tree.bind("<Button-3>", self._show_folder_context_menu)
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def _create_file_icons(self):
        colors = {
            "folder": (245, 185, 55),
            "file": (148, 163, 184),
            "image": (45, 180, 145),
            "video": (217, 92, 92),
            "archive": (164, 125, 219),
            "application": (75, 145, 210),
        }
        self.file_icons = {}
        for key, color in colors.items():
            image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            if key == "folder":
                draw.polygon([(2, 5), (8, 5), (10, 7), (18, 7), (18, 17), (2, 17)], fill=color)
                draw.line([(2, 5), (8, 5), (10, 7), (18, 7)], fill=(255, 220, 115), width=1)
            else:
                draw.polygon([(4, 2), (13, 2), (17, 6), (17, 18), (4, 18)], fill=color)
                draw.polygon([(13, 2), (13, 6), (17, 6)], fill=(226, 232, 240))
                draw.line([(7, 10), (14, 10)], fill=(255, 255, 255), width=1)
                draw.line([(7, 13), (14, 13)], fill=(255, 255, 255), width=1)
            self.file_icons[key] = ImageTk.PhotoImage(image)

    def _populate_folder_view(self, tree, folder, include_subfolders=True):
        tree.delete(*tree.get_children())
        tree._folder_paths = {}
        tree._loaded_folders = set()
        tree._include_subfolders = include_subfolders
        path = Path(folder.strip()) if folder.strip() else None
        tree._root_path = path
        if path is None:
            return
        self._insert_folder_entries(tree, "", path)

    def _insert_folder_entries(self, tree, parent, path):
        try:
            entries = sorted(os.scandir(path), key=lambda entry: (not entry.is_dir(follow_symlinks=False), entry.name.lower()))
            for entry in entries:
                is_directory = entry.is_dir(follow_symlinks=False)
                if is_directory and not tree._include_subfolders:
                    continue
                if is_directory:
                    item_id = tree.insert(
                        parent,
                        "end",
                        text=f"{entry.name}/",
                        image=tree._file_icons["folder"],
                        values=("<DIR>",),
                    )
                    tree._folder_paths[item_id] = Path(entry.path)
                    tree.insert(item_id, "end", text="")
                else:
                    try:
                        size = f"{entry.stat(follow_symlinks=False).st_size:,}"
                    except OSError:
                        size = "?"
                    tree.insert(
                        parent,
                        "end",
                        text=entry.name,
                        image=tree._file_icons[icon_key_for_filename(entry.name)],
                        values=(size,),
                    )
            tree._loaded_folders.add(str(path))
        except (OSError, PermissionError):
            tree.insert(parent, "end", text="Folder No Longer Available on this Drive", values=("",))
            play_standard_alert_beep()

    def _expand_folder_item(self, event):
        tree = event.widget
        item_id = tree.focus()
        path = tree._folder_paths.get(item_id)
        if path is None or str(path) in tree._loaded_folders:
            return
        tree.delete(*tree.get_children(item_id))
        self._insert_folder_entries(tree, item_id, path)

    def _show_folder_context_menu(self, event):
        """Source/Destination right-click: New Folder inside the clicked folder, the clicked file's
        folder, or (on empty space) the top-level folder; plus Delete when a file was clicked."""
        tree = event.widget
        row = tree.identify_row(event.y)
        if row in tree._folder_paths:
            target_item, target_path = row, tree._folder_paths[row]
        else:
            target_item = tree.parent(row) if row else ""
            target_path = tree._folder_paths.get(target_item) if target_item else tree._root_path
        if row:
            tree.selection_set(row)
            tree.focus(row)
        available = target_path is not None and target_path.is_dir() and not self._operation_is_running()
        place = (target_path.name or str(target_path)) if target_path is not None else "folder"
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=f"New Folder in '{place}'…",
            command=lambda: self._create_folder_in_tree(tree, target_item, target_path),
            state=tk.NORMAL if available else tk.DISABLED,
        )
        file_name = tree.item(row, "text") if row and row not in tree._folder_paths else ""
        if file_name and target_path is not None and (target_path / file_name).is_file():
            menu.add_separator()
            menu.add_command(
                label=f"Delete '{file_name}'",
                command=lambda: self._delete_file_in_tree(tree, target_item, target_path, file_name),
                state=tk.NORMAL if send2trash is not None and not self._operation_is_running() else tk.DISABLED,
            )
        menu.tk_popup(event.x_root, event.y_root)

    def _delete_file_in_tree(self, tree, parent_item, parent_path, file_name):
        file_path = parent_path / file_name
        if not messagebox.askyesno(
            "Delete File",
            f"Send this file to the Recycle Bin?\n\n{file_path}",
            icon=messagebox.WARNING,
            parent=self,
        ):
            return
        try:
            send2trash(str(file_path))
        except OSError as error:
            messagebox.showerror("Delete File", f"Could not delete the file:\n{file_path}\n\n{error}", parent=self)
            return
        self._log(f"Sent file to the Recycle Bin: {file_path}")
        self._reload_folder_level(tree, parent_item, parent_path)
        if parent_item:
            tree.item(parent_item, open=True)
            tree.selection_set(parent_item)
            tree.focus(parent_item)

    def _create_folder_in_tree(self, tree, parent_item, parent_path):
        name = "New Folder"
        while True:
            name = simpledialog.askstring(
                "New Folder",
                f"Create a new folder in:\n{parent_path}\n\nFolder name:",
                initialvalue=name,
                parent=self,
            )
            if name is None:
                return
            name = name.strip()
            problem = new_folder_name_problem(name)
            if problem is None and (parent_path / name).exists():
                problem = f"'{name}' already exists in this folder."
            if problem is None:
                break
            messagebox.showerror("New Folder", problem, parent=self)
        new_path = parent_path / name
        try:
            new_path.mkdir()
        except OSError as error:
            messagebox.showerror("New Folder", f"Could not create the folder:\n{new_path}\n\n{error}", parent=self)
            return
        self._log(f"Created folder: {new_path}")
        if not tree._include_subfolders:
            self._log("Folders aren't listed while 'Include subfolders' is off.")
            return
        self._reload_folder_level(tree, parent_item, parent_path)
        if parent_item:
            tree.item(parent_item, open=True)
        for item in tree.get_children(parent_item):
            if tree._folder_paths.get(item) == new_path:
                tree.selection_set(item)
                tree.focus(item)
                tree.see(item)
                break

    def _reload_folder_level(self, tree, item_id, path):
        """Re-read one folder's entries into the tree; folders below it are re-read when next expanded."""
        def forget(node):
            for child in tree.get_children(node):
                forget(child)
                tree._folder_paths.pop(child, None)

        forget(item_id)
        tree._loaded_folders = {
            loaded for loaded in tree._loaded_folders if Path(loaded) != path and path not in Path(loaded).parents
        }
        tree.delete(*tree.get_children(item_id))
        self._insert_folder_entries(tree, item_id, path)

    def _include_subfolders_changed(self):
        self.refresh_folder_views()
        self._profile_field_changed()

    def refresh_folder_views(self):
        include_subfolders = self.include_subfolders_var.get()
        self._populate_folder_view(
            self.source_tree,
            self.source_var.get(),
            include_subfolders=include_subfolders,
        )
        self._populate_folder_view(
            self.destination_tree,
            self.destination_var.get(),
            include_subfolders=include_subfolders,
        )

    def _operation_is_running(self):
        return (self.active_process is not None and self.active_process.poll() is None) or (
            self.active_sync_thread is not None and self.active_sync_thread.is_alive()
        )

    def _start_destination_auto_refresh(self):
        if self._destination_refresh_scheduled:
            return
        self._destination_refresh_scheduled = True
        self.after(2000, self._auto_refresh_destination_view)

    def _refresh_folder_views_for_active_mode(self):
        # Backup/Mirror/Compare only ever change Destination; refreshing Source
        # too would reset the user's expanded folder state there for no reason.
        # Move removes files from Source, and Sync changes both sides, so those
        # two modes need the Source tree refreshed as well.
        if self.mode_var.get() in ("move", "twoway"):
            self.refresh_folder_views()
        else:
            self._populate_folder_view(
                self.destination_tree,
                self.destination_var.get(),
                include_subfolders=self.include_subfolders_var.get(),
            )

    def _auto_refresh_destination_view(self):
        if not self._operation_is_running():
            self._destination_refresh_scheduled = False
            return
        self._refresh_folder_views_for_active_mode()
        self.after(2000, self._auto_refresh_destination_view)

    def browse_source(self):
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            initialdir=folder_dialog_initialdir(self.source_var.get()),
        )
        if folder:
            self.source_var.set(folder)
            self.refresh_folder_views()

    def browse_destination(self):
        folder = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=folder_dialog_initialdir(self.destination_var.get()),
        )
        if folder:
            self.destination_var.set(folder)
            self.refresh_folder_views()

    def open_about(self):
        if getattr(self, "about_window", None) is not None and self.about_window.winfo_exists():
            self.about_window.lift()
            self.about_window.focus_force()
            return
        self.about_window = SplashScreen(self)

    def show_coffee(self):
        show_support(self, APP_NAME, reason="It helps keep the app going and improving.")

    def _update_job_profile_label(self, *_args):
        name = self.job_name.get().strip() or "Untitled"
        self.job_profile_label.config(text=f"Showing Job Profile: {name}")

    def open_backup_info(self):
        if getattr(self, "backup_info_window", None) is not None and self.backup_info_window.winfo_exists():
            self.backup_info_window.lift()
            self.backup_info_window.focus_force()
            return

        dialog = tk.Toplevel(self)
        self.backup_info_window = dialog
        dialog.title("Backup Info")
        dialog.configure(bg="#111827")
        dialog.resizable(False, False)
        dialog.transient(self)

        content = tk.Frame(dialog, bg="#111827", padx=18, pady=16)
        content.pack(fill="both", expand=True)
        tk.Label(
            content,
            text="Backup modes",
            font=("Segoe UI", 12, "bold"),
            bg="#111827",
            fg="#e2e8f0",
        ).pack(anchor="w", pady=(0, 12))

        explanations = (
            ("BACKUP", "Copies new and changed files to the destination."),
            ("MIRROR", "Makes the Destination mirror the Source - including deletions. \nUseful when a large project is completed, thus making the \nDestination folder an exact copy of the Source Folder. \nAny old temp or scratch files in the Destination Folder \nthat are not present in the Source Folder will be removed. \n\nThe Source Folder is the Master Reference."),
            ("MOVE", "Copies files to the destination and removes them from the source."),
            ("COMPARE", "Lists what would be copied without changing either folder."),
            ("SYNC", "Copies new and changed files in both directions and propagates \ndeletions between them, using each job's saved history. \nDeletions go to the Recycle Bin. If a file changed on both sides, the newer \nversion keeps its name and the older version is kept alongside it, \non both sides, as 'name (Sync Conflict - date).ext'.\n\n e.g.: report.docx → report (Sync Conflict - 2026-09-24).docx"),
        )
        for mode, explanation in explanations:
            row = tk.Frame(content, bg="#111827")
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=f"{mode}: ",
                font=("Segoe UI", 10, "bold"),
                bg="#111827",
                fg="#e2e8f0",
            ).pack(side="left", anchor="n")
            tk.Label(
                row,
                text=explanation,
                font=("Segoe UI", 10),
                bg="#111827",
                fg="#cbd5e1",
                wraplength=420,
                justify="left",
            ).pack(side="left", anchor="n")

        tk.Button(
            content,
            text="OK",
            command=dialog.destroy,
            bg="#1f2937",
            fg="#e2e8f0",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=16,
        ).pack(anchor="e", pady=(14, 0))

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        dialog.focus_force()

    def _log(self, message, tag=None):
        self.log_widget.insert("end", f"{message}\n", tag)
        self.log_widget.see("end")
        self.update_idletasks()

    def _current_selection_offline_drives(self):
        """Offline drives for the selected job. Returns [] for group/all (those run per-job with skip+report)."""
        selected = self._selected_sidebar_item()
        if not selected or selected[0] != "job":
            self._last_offline_transition = []
            return []
        paths = [self.source_var.get(), self.destination_var.get()]
        drives = {extract_drive_letter(path) for path in paths if extract_drive_letter(path)}
        # Route through the tracked/alerted status check, not a silent is_drive_online()
        # call, so a drive found offline here still triggers the sound + popup.
        self._last_offline_transition = self._update_drive_statuses(drives) if drives else []
        return sorted(drive for drive in drives if not self.known_drive_status.get(drive, True))

    def _group_selection_offline_job_names(self):
        selected = self._selected_sidebar_item()
        if not selected or selected[0] not in ("group", "all"):
            return []
        job_drives = []
        all_drives = set()
        for job in self._jobs_for_selection():
            paths = (job.get("source", ""), job.get("destination", ""))
            drives = {extract_drive_letter(path) for path in paths if extract_drive_letter(path)}
            job_drives.append((str(job.get("name", "Untitled")), drives))
            all_drives |= drives
        if all_drives:
            self._update_drive_statuses(all_drives)
        return [
            name for name, drives in job_drives
            if any(not self.known_drive_status.get(drive, True) for drive in drives)
        ]

    def _update_run_button_state(self):
        offline = self._current_selection_offline_drives()
        self._last_selection_offline_drives = offline
        if hasattr(self, "run_button"):
            self.run_button.configure(state="disabled" if offline else "normal")
        if hasattr(self, "drive_warning_label"):
            if offline:
                self.drive_warning_label.config(text=f"\u26a0 Drive {', '.join(offline)}: offline - this profile cannot run.")
                return
            affected_group_jobs = self._group_selection_offline_job_names()
            if affected_group_jobs:
                self.drive_warning_label.config(
                    text=f"\u26a0 Offline drive detected - {len(affected_group_jobs)} job(s) in this selection will be skipped: {', '.join(affected_group_jobs)}"
                )
            else:
                self.drive_warning_label.config(text="")

    def _check_drive_availability(self):
        drives = collect_drive_letters(self.jobs)
        self.known_drive_status = {drive: is_drive_online(drive) for drive in drives}
        offline_drives = sorted(drive for drive, online in self.known_drive_status.items() if not online)
        if not offline_drives:
            self._update_run_button_state()
            self._log(f"Startup check: {len(drives)} drive letter(s) referenced by job profiles, all online.")
        else:
            self._notify_offline_drives(offline_drives)
        self._schedule_drive_poll()

    def _affected_jobs_for_drives(self, drives) -> list:
        drives = set(drives)
        return sorted({
            str(job.get("name", "Untitled"))
            for job in self.jobs
            if extract_drive_letter(job.get("source", "")) in drives
            or extract_drive_letter(job.get("destination", "")) in drives
        })

    def _notify_offline_drives(self, offline_drives):
        affected_jobs = self._affected_jobs_for_drives(offline_drives)
        self._log(
            f"WARNING: Offline/disconnected drive(s) detected: {', '.join(offline_drives)}. "
            f"Affected job(s): {', '.join(affected_jobs) if affected_jobs else 'unknown'}.",
            "job_report",
        )
        play_error_sound()
        message = (
            "The following drive letter(s) used by your backup profiles are OFFLINE or unreachable:\n\n"
            + "\n".join(f"  - {drive}" for drive in offline_drives)
            + "\n\nAffected job profile(s):\n"
            + "\n".join(f"  - {name}" for name in affected_jobs)
            + "\n\nPlease reconnect the drive(s)/cable(s) before running these backups."
        )
        messagebox.showwarning("Offline Drive Detected", message, parent=self)
        self._update_run_button_state()

    def _schedule_drive_poll(self):
        self.after(DRIVE_POLL_INTERVAL_MS, self._poll_drive_status)

    def _update_drive_statuses(self, drives) -> list:
        newly_offline = []
        newly_online = []
        for drive in drives:
            online_now = is_drive_online(drive)
            was_online = self.known_drive_status.get(drive, True)
            if was_online and not online_now:
                newly_offline.append(drive)
            elif not was_online and online_now:
                newly_online.append(drive)
            self.known_drive_status[drive] = online_now
        if newly_offline:
            self._notify_offline_drives(sorted(newly_offline))
        if newly_online:
            self._log(f"Drive(s) reconnected: {', '.join(sorted(newly_online))}.", "job_report")
            play_completion_chime()
            self._update_run_button_state()
        return newly_offline

    def _poll_drive_status(self):
        # Slow safety-net: catches cases WM_DEVICECHANGE misses (silent
        # power loss, flaky enclosures, mapped network drives going dark).
        if not self.winfo_exists():
            return
        drives = collect_drive_letters(self.jobs)
        for drive in list(self.known_drive_status):
            if drive not in drives:
                del self.known_drive_status[drive]
        self._update_drive_statuses(drives)
        self._schedule_drive_poll()

    # --- Event-driven detection via WM_DEVICECHANGE ------------------------

    def _install_drive_change_watcher(self) -> None:
        self.update_idletasks()
        hwnd = self.winfo_id()
        self._new_wndproc = WNDPROCTYPE(self._drive_watcher_wndproc)
        self._old_wndproc = _user32.SetWindowLongPtrW(
            hwnd, GWLP_WNDPROC, self._new_wndproc
        )

    def _uninstall_drive_change_watcher(self) -> None:
        if self._old_wndproc is None:
            return
        hwnd = self.winfo_id()
        _user32.SetWindowLongPtrW(hwnd, GWLP_WNDPROC, self._old_wndproc)
        self._old_wndproc = None

    def destroy(self):
        self._uninstall_drive_change_watcher()
        super().destroy()

    def _drive_watcher_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DEVICECHANGE and wparam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
            self._handle_device_change(lparam)
        return _user32.CallWindowProcW(self._old_wndproc, hwnd, msg, wparam, lparam)

    def _handle_device_change(self, lparam) -> None:
        if not lparam:
            return
        header = DEV_BROADCAST_HDR.from_address(lparam)
        if header.dbch_devicetype != DBT_DEVTYP_VOLUME:
            return
        volume = DEV_BROADCAST_VOLUME.from_address(lparam)
        changed_drives = unitmask_to_drive_letters(volume.dbcv_unitmask)
        # Defer to the Tk event loop's idle cycle rather than doing work
        # (messageboxes, sounds) directly inside the raw window-proc callback.
        self.after_idle(lambda: self._refresh_drive_status(changed_drives))

    def _refresh_drive_status(self, changed_drives) -> None:
        if not self.winfo_exists():
            return
        tracked = collect_drive_letters(self.jobs)
        drives = [drive for drive in changed_drives if drive in tracked]
        if drives:
            self._update_drive_statuses(drives)

    def _should_log_line(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.endswith("%"):
            try:
                float(stripped[:-1])
                return False
            except ValueError:
                pass
        return True

    def _normalize_log_line(self, text: str) -> str:
        text = text.replace("\t", " ").lstrip()
        if text.startswith("Total") and "Copied" in text and "Skipped" in text:
            return f"{' ' * 13}{text}"
        return text

    def _stream_process_output(self, process, output_queue, log_mode):
        try:
            if process.stdout is not None:
                for line in iter(process.stdout.readline, ""):
                    text = line.rstrip()
                    normalized = self._normalize_log_line(text)
                    if log_mode != "No Logs" and self._should_log_line(normalized):
                        output_queue.put(normalized)
            if process.stderr is not None:
                for line in iter(process.stderr.readline, ""):
                    text = line.rstrip()
                    normalized = self._normalize_log_line(text)
                    if log_mode != "No Logs" and self._should_log_line(normalized):
                        output_queue.put(normalized)
        except Exception as exc:
            output_queue.put(f"Stream error: {exc}")

    def _drain_output_queue(self, output_queue):
        lines = []
        while len(lines) < 1000:
            try:
                lines.append(output_queue.get_nowait())
            except queue.Empty:
                break
        if lines:
            self.log_widget.insert("end", "\n".join(lines) + "\n")
            self.log_widget.see("end")
            self.update_idletasks()

    def _poll_process(self, process, output_thread, output_queue, final_message):
        self._drain_output_queue(output_queue)
        if process.poll() is None or output_thread.is_alive() or not output_queue.empty():
            self.after(100, lambda: self._poll_process(process, output_thread, output_queue, final_message))
            return

        code = process.returncode
        aborted = self.operation_aborted
        self.active_process = None
        self.process_paused = False
        self.operation_aborted = False
        self.pause_button.configure(text="Pause")
        self._set_operation_controls(False)
        self._refresh_folder_views_for_active_mode()
        self._log(f"Operation aborted with exit code {code}." if aborted else final_message.format(code=code))
        if self.batch_job_names:
            job_ok = not aborted and is_successful_robocopy_exit_code(code)
            reason = None if job_ok else f"Robocopy exit code {code}."
            self.batch_job_results.append((self.batch_job_names[-1], reason))
        if self.pending_jobs and not aborted:
            self.after_idle(self._run_next_job)
        else:
            self._log_job_batch_report()
            self.pending_jobs = []
            if aborted or not is_successful_robocopy_exit_code(code):
                play_error_sound()
            else:
                play_completion_chime()

    def _log_job_batch_report(self):
        if not self.batch_job_names:
            return
        count = len(self.batch_job_names)
        failures = [(name, reason) for name, reason in self.batch_job_results if reason]
        succeeded = count - len(failures)
        self._log(f"Backup report: {count} JOB{'s' if count != 1 else ''} run ({succeeded} succeeded, {len(failures)} failed).", "job_report")
        for name in self.batch_job_names:
            failure_reason = next((reason for job_name, reason in failures if job_name == name), None)
            status = f"FAILED - {failure_reason}" if failure_reason else "OK"
            self._log(f"  JOB profile: {name} [{status}]", "job_report")
        self.batch_job_names = []
        self.batch_job_results = []

    def _launch_sync_job(self, source, destination, include_subfolders, log_mode):
        if send2trash is None:
            self._set_operation_controls(False)
            self._log("Sync requires the 'send2trash' package, which is not installed.")
            play_error_sound()
            messagebox.showerror(
                "Missing dependency",
                "Sync mode requires the 'send2trash' package.\n\nInstall it with:\n\npip install send2trash",
                parent=self,
            )
            return

        self._log(f"Running Sync: {source} <-> {destination}")
        self.sync_pause_event.set()
        self.sync_abort_event.clear()
        self.process_paused = False
        self.operation_aborted = False
        log_queue = queue.Queue()
        result_box = {}
        thread = threading.Thread(
            target=self._run_sync_worker,
            args=(source, destination, include_subfolders, log_queue, result_box),
            daemon=True,
        )
        self.active_sync_thread = thread
        self._set_operation_controls(True)
        self._start_destination_auto_refresh()
        thread.start()
        self.after(100, lambda: self._poll_sync_job(thread, log_queue, result_box, log_mode, source, destination))

    def _run_sync_worker(self, source, destination, include_subfolders, log_queue, result_box):
        try:
            result_box["result"] = run_sync_engine(
                source,
                destination,
                include_subfolders,
                self.sync_pause_event,
                self.sync_abort_event,
                log_queue,
            )
        except Exception as exc:
            log_queue.put(f"Sync ERROR: {exc}")
            result_box["result"] = SyncResult(success=False, errors=[str(exc)])

    def _poll_sync_job(self, thread, log_queue, result_box, log_mode, source, destination):
        if log_mode == "No Logs":
            while True:
                try:
                    log_queue.get_nowait()
                except queue.Empty:
                    break
        else:
            self._drain_output_queue(log_queue)
        if thread.is_alive():
            self.after(100, lambda: self._poll_sync_job(thread, log_queue, result_box, log_mode, source, destination))
            return

        result = result_box.get("result") or SyncResult(success=False, errors=["Sync worker exited unexpectedly."])
        aborted = self.operation_aborted or result.aborted
        self.active_sync_thread = None
        self.process_paused = False
        self.operation_aborted = False
        self.pause_button.configure(text="Pause")
        self._set_operation_controls(False)
        self._refresh_folder_views_for_active_mode()

        if aborted:
            self._log("Sync aborted.")
        else:
            summary = (
                f"Sync complete. Copied {result.copied_to_dest} to Destination, "
                f"{result.copied_to_source} to Source, deleted {result.deleted_from_dest} from Destination, "
                f"{result.deleted_from_source} from Source, {result.conflicts} conflict(s)."
            )
            self._log(summary)
            for error in result.errors:
                self._log(f"Sync error: {error}", "job_report")
            if result.conflicts:
                job_name = self.batch_job_names[-1] if self.batch_job_names else (self.job_name.get() or "this Sync job")
                messagebox.showwarning(
                    "Sync Conflicts Found",
                    f"Sync job '{job_name}' found {result.conflicts} file(s) changed on both "
                    "Source and Destination since the last sync.\n\n"
                    "Please examine these files and make any adjustments needed.\n\n"
                    "Click OK to view Report.",
                    parent=self,
                )
                self._launch_sync_conflict_report(job_name, source, destination, result)

        if self.batch_job_names:
            job_ok = not aborted and result.success
            reason = None if job_ok else "; ".join(result.errors) or "Sync aborted."
            self.batch_job_results.append((self.batch_job_names[-1], reason))
        if self.pending_jobs and not aborted:
            self.after_idle(self._run_next_job)
        else:
            self._log_job_batch_report()
            self.pending_jobs = []
            if aborted or not result.success:
                play_error_sound()
            else:
                play_completion_chime()

    def _launch_sync_conflict_report(self, job_name, source, destination, result: "SyncResult"):
        header_lines = [
            "EZee-Backup Sync Conflict Report",
            f"Job: {job_name}",
            f"Source: {source}",
            f"Destination: {destination}",
            f"Conflicts found: {result.conflicts}",
            "",
            "The newer version of each file below was kept under its original name.",
            "The older version was kept alongside it, on both sides, as",
            "'name (Sync Conflict - date).ext'. Please examine these files and make",
            "any adjustments needed.",
        ]
        report_text = "\n".join(header_lines) + "\n\n" + "\n\n".join(result.conflict_details)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="ezee-backup-sync-conflicts-",
                encoding="utf-8",
                delete=False,
            ) as report_file:
                report_file.write(report_text)
                report_path = report_file.name
            subprocess.Popen(["notepad.exe", report_path])
        except OSError as exc:
            messagebox.showerror("Notepad", f"Unable to launch Notepad:\n{exc}", parent=self)

    def refresh_jobs_list(self, collapsed=False):
        self.job_tree.delete(*self.job_tree.get_children())
        expand = not collapsed
        groups = {}
        for index, job in enumerate(self.jobs):
            group = str(job.get("group", "")).strip()
            groups.setdefault(group, []).append((index, job))
        all_jobs = self.job_tree.insert("", "end", text="All Jobs", values=("all", ""), open=expand)
        for index, job in enumerate(self.jobs):
            mode = str(job.get("mode", "backup")).lower()
            self.job_tree.insert(all_jobs, "end", text=job.get("name", "Untitled"), values=("job", index), tags=(mode,))
        for group, members in groups.items():
            if not group:
                continue
            parent = self.job_tree.insert("", "end", text=group, values=("group", group), open=expand)
            for index, job in members:
                mode = str(job.get("mode", "backup")).lower()
                self.job_tree.insert(parent, "end", text=job.get("name", "Untitled"), values=("job", index), tags=(mode,))
        children = self.job_tree.get_children()
        if children:
            first_job = self.job_tree.get_children(children[0])
            self.job_tree.selection_set(first_job[0] if first_job else children[0])

    def _selected_sidebar_item(self):
        selected = self.job_tree.selection()
        if not selected:
            return None
        kind, value = self.job_tree.item(selected[0]).get("values", (None, None))
        return kind, value

    def _set_profile_modified(self, modified):
        self._profile_modified = modified
        if hasattr(self, "save_changes_button"):
            save_color = "#ffff00" if modified else "#ffffff"
            self.save_changes_button.configure(
                fg=save_color,
                activeforeground=save_color,
                state=tk.NORMAL if modified else tk.DISABLED,
            )
        if hasattr(self, "edit_menu"):
            menu_state = tk.NORMAL if modified else tk.DISABLED
            self.edit_menu.entryconfigure("Save Changes", state=menu_state)
            self.edit_menu.entryconfigure("Forget Changes", state=menu_state)
        if hasattr(self, "forget_changes_button"):
            forget_color = "#ffa500" if modified else "#ffffff"
            self.forget_changes_button.configure(
                fg=forget_color,
                activeforeground=forget_color,
                state=tk.NORMAL if modified else tk.DISABLED,
            )

    def _profile_field_changed(self, *_args):
        if self._loading_job:
            return
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "job":
            self._set_profile_modified(True)
        self._update_run_button_state()

    def _select_sidebar_item(self, _event=None):
        selected = self._selected_sidebar_item()
        if not selected:
            return
        repeat_offline_selection = False
        if selected[0] == "job":
            self.load_selected_job(int(selected[1]))
            # load_selected_job() already ran the drive check via _update_run_button_state();
            # capture its verdict now, before the redundant call below overwrites it.
            repeat_offline_selection = bool(self._last_selection_offline_drives) and not self._last_offline_transition
        else:
            self._set_profile_modified(False)
            self.source_var.set("")
            self.destination_var.set("")
            self.refresh_folder_views()
            if selected[0] == "group":
                job_count = len(jobs_for_sidebar_selection(self.jobs, "group", selected[1]))
                self.job_profile_label.config(
                    text=f"A Group Profile is selected with {job_count} Jobs"
                )
            elif selected[0] == "all":
                self.job_profile_label.config(text=f"All Jobs is selected with {len(self.jobs)} Jobs")
            else:
                self._update_job_profile_label()
        self._update_run_button_state()
        if repeat_offline_selection:
            play_standard_alert_beep()

    def _show_job_context_menu(self, event):
        item_id = self.job_tree.identify_row(event.y)
        if not item_id:
            return
        self.job_tree.selection_set(item_id)
        selected = self._selected_sidebar_item()
        if not selected:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="Rename",
            command=lambda: self.rename_sidebar_item(selected[0], selected[1]),
            state=tk.DISABLED if selected[0] == "all" else tk.NORMAL,
        )
        if selected[0] == "job":
            parent_id = self.job_tree.parent(item_id)
            parent_kind = self.job_tree.item(parent_id).get("values", (None, None))[0]
            menu.add_command(label="Duplicate", command=lambda: self.duplicate_job(int(selected[1])))
            menu.add_command(
                label="Add to Group",
                command=lambda: self.add_job_to_group(int(selected[1]), event.x_root, event.y_root),
            )
            menu.add_command(
                label="Remove from Group",
                command=lambda: self.remove_job_from_group(int(selected[1])),
                state=tk.DISABLED if parent_kind == "all" else tk.NORMAL,
            )
        elif selected[0] == "group":
            menu.add_command(label="Delete Group", command=lambda: self.delete_group(selected[1]))
        menu.tk_popup(event.x_root, event.y_root)

    def _load_initial_job(self):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "job":
            self.load_selected_job(int(selected[1]))

    def save_current_job(self):
        if not has_valid_folder_pair(self.source_var.get(), self.destination_var.get()):
            messagebox.showerror("Missing folders", "Please choose both a source and destination folder before saving a job.")
            return
        name = simpledialog.askstring(
            "Save Job",
            "Job name:",
            initialvalue=self.job_name.get().strip() or "New Job",
            parent=self,
        )
        if not name or not name.strip():
            return
        name = name.strip()
        self.job_name.set(name)
        job = {
            "name": name,
            "source": self.source_var.get(),
            "destination": self.destination_var.get(),
            "mode": self.mode_var.get(),
            "include_subfolders": self.include_subfolders_var.get(),
        }
        existing = [item for item in self.jobs if item.get("name") != name]
        old_job = next((item for item in self.jobs if item.get("name") == name), None)
        if old_job and old_job.get("group"):
            job["group"] = old_job["group"]
        existing.append(job)
        self.jobs = existing
        save_jobs(self.jobs, job_file_path())
        self._set_profile_modified(False)
        self.refresh_jobs_list(collapsed=True)
        self._focus_job_in_sidebar(len(self.jobs) - 1)
        self._log(f"Saved job: {name}")

    def _focus_job_in_sidebar(self, index, group=None):
        """Open one sidebar group ("All Jobs" when group is None) and select, focus and scroll to the job's row in it.

        With index None, the group's first row is used. Returns False if the group isn't in the tree.
        """
        parent = None
        for node in self.job_tree.get_children():
            kind, value = self.job_tree.item(node).get("values", (None, None))
            if (group is None and kind == "all") or (group is not None and kind == "group" and str(value) == group):
                parent = node
                break
        if parent is None:
            return False
        self.job_tree.item(parent, open=True)
        for item in self.job_tree.get_children(parent):
            kind, value = self.job_tree.item(item).get("values", (None, None))
            if kind == "job" and (index is None or int(value) == index):
                self.job_tree.selection_set(item)
                self.job_tree.focus(item)
                self.job_tree.see(item)
                self.job_tree.focus_set()
                break
        return True

    def save_job_changes(self):
        selected = self._selected_sidebar_item()
        if not selected or selected[0] != "job":
            messagebox.showwarning("No job selected", "Select a job before saving changes.")
            return
        if not has_valid_folder_pair(self.source_var.get(), self.destination_var.get()):
            messagebox.showerror("Missing folders", "Please choose both a source and destination folder before saving changes.")
            return
        index = int(selected[1])
        job = self.jobs[index]
        job.update(
            source=self.source_var.get(),
            destination=self.destination_var.get(),
            mode=self.mode_var.get(),
            include_subfolders=self.include_subfolders_var.get(),
        )
        save_jobs(self.jobs, job_file_path())
        self._set_profile_modified(False)
        self._update_job_rows(index)
        self._log(f"Saved changes to job: {job.get('name', 'Untitled')}")

    def _update_job_rows(self, index):
        """Refresh the mode tag of a job's sidebar rows in place, keeping the tree's selection and expansion."""
        mode = str(self.jobs[index].get("mode", "backup")).lower()
        for parent in self.job_tree.get_children():
            for item in self.job_tree.get_children(parent):
                kind, value = self.job_tree.item(item).get("values", (None, None))
                if kind == "job" and int(value) == index:
                    self.job_tree.item(item, tags=(mode,))

    def forget_changes(self):
        self.jobs, load_notice = load_jobs_with_report(job_file_path())
        self._set_profile_modified(False)
        self.refresh_jobs_list()
        self._load_initial_job()
        self._log("Forgot unsaved changes and reloaded JOB profiles.")
        if load_notice:
            self._report_job_file_recovery(load_notice)

    def open_restore_older_version(self):
        """Edit > Restore Master Jobs Profile from History: pick a dated copy of the JOB file and make it current."""
        if self._operation_is_running():
            messagebox.showinfo(
                "Restore Master Jobs Profile", "Please wait until the current operation finishes.", parent=self
            )
            return
        target = job_file_path()
        dated_copies = history_files(target)
        if not dated_copies:
            messagebox.showinfo(
                "Restore Master Jobs Profile",
                f"There are no dated copies of your job profiles yet.\n\nThey are kept in:\n{history_dir(target)}",
                parent=self,
            )
            return
        _current_jobs, current_raw, _problem = read_jobs_file(target)
        current_jobs = _current_jobs or []

        dialog = tk.Toplevel(self)
        dialog.title("Restore Master Jobs Profile")
        dialog.configure(bg="#111827")
        dialog.transient(self)
        dialog.minsize(760, 380)

        tk.Label(
            dialog,
            text="Choose an earlier version of your job profiles to restore:",
            bg="#111827", fg="#e2e8f0", font=("Segoe UI", 10, "bold"),
        ).pack(padx=18, pady=(16, 2), anchor="w")
        tk.Label(
            dialog,
            text="Your current profiles are kept as a dated copy first, so a restore can be undone here.",
            bg="#111827", fg="#94a3b8", font=("Segoe UI", 9),
        ).pack(padx=18, pady=(0, 8), anchor="w")

        table_frame = tk.Frame(dialog, bg="#111827")
        table_frame.pack(fill="both", expand=True, padx=18)
        columns = ("when", "jobs", "groups", "changes")
        table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", height=12)
        for column, heading, width, stretch in (
            ("when", "Saved", 190, False),
            ("jobs", "Jobs", 55, False),
            ("groups", "Groups", 60, False),
            ("changes", "Restoring this version would...", 420, True),
        ):
            table.heading(column, text=heading, anchor="w")
            table.column(column, width=width, stretch=stretch, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        table.tag_configure("unusable", foreground="#9ca3af")

        rows = {}
        for stamp, dated in dated_copies:
            dated_jobs, dated_raw, problem = read_jobs_file(dated)
            when = stamp.strftime("%a %d %b %Y  %H:%M:%S")
            if dated_jobs is None:
                values = (when, "-", "-", f"Cannot be used: {problem}")
                tags = ("unusable",)
            else:
                groups = {str(job.get("group", "")).strip() for job in dated_jobs} - {""}
                if dated_raw == current_raw:
                    changes = "Nothing - this is the current version"
                else:
                    changes = summarize_job_changes(current_jobs, dated_jobs)
                values = (when, len(dated_jobs), len(groups), changes)
                tags = ()
            item = table.insert("", "end", values=values, tags=tags)
            rows[item] = (stamp, dated, dated_jobs is not None, dated_raw == current_raw, values[3])
        first = table.get_children()[0]
        table.selection_set(first)
        table.focus(first)

        def restore():
            selection = table.selection()
            if not selection:
                return
            stamp, dated, usable, is_current, changes = rows[selection[0]]
            if not usable:
                messagebox.showerror("Restore Master Jobs Profile", "That dated copy is damaged and cannot be used.", parent=dialog)
                return
            if is_current:
                messagebox.showinfo("Restore Master Jobs Profile", "That version is already your current job profiles.", parent=dialog)
                return
            message = (
                f"Restore your job profiles as they were on {stamp.strftime('%d %B %Y at %H:%M:%S')}?\n\n"
                f"{changes.replace(' | ', chr(10))}\n\n"
                "Your current profiles will be kept as a dated copy, so you can undo this."
            )
            if getattr(self, "_profile_modified", False):
                message += "\n\nUnsaved changes to the current job will be lost."
            if not messagebox.askyesno("Restore Master Jobs Profile", message, icon="warning", parent=dialog):
                return
            try:
                restored = restore_history_copy(target, dated)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Restore Master Jobs Profile", f"The restore did not complete:\n{exc}", parent=dialog)
                return
            dialog.destroy()
            self._apply_replaced_jobs(
                restored,
                f"Restored job profiles from the dated copy saved {stamp.strftime('%d %B %Y at %H:%M:%S')} "
                f"({len(restored)} jobs).",
            )

        buttons = tk.Frame(dialog, bg="#111827")
        buttons.pack(fill="x", padx=18, pady=(10, 16))
        tk.Button(
            buttons, text="Cancel", command=dialog.destroy,
            bg="#1f2937", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 10, "bold"), padx=12,
        ).pack(side="right")
        tk.Button(
            buttons, text="Restore", command=restore,
            bg="#38bdf8", fg="#0f172a", activebackground="#7dd3fc",
            relief="flat", font=("Segoe UI", 10, "bold"), padx=12,
        ).pack(side="right", padx=(0, 8))
        tk.Button(
            buttons, text="Open Folder", command=lambda: os.startfile(history_dir(target)),
            bg="#1f2937", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff",
            relief="flat", font=("Segoe UI", 10, "bold"), padx=12,
        ).pack(side="left")

        table.bind("<Double-1>", lambda _event: restore())
        dialog.bind("<Return>", lambda _event: restore())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self.restore_dialog = dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_reqheight()) // 3)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        table.focus_set()

    def _apply_replaced_jobs(self, jobs, log_message):
        """Show a newly restored or imported job list, and check the drives it uses."""
        self.jobs = jobs
        self._set_profile_modified(False)
        self.refresh_jobs_list()
        self._load_initial_job()
        self._log(log_message, "job_report")
        # The new jobs may use drives the app was not watching; check them now (alerts if offline).
        drives = collect_drive_letters(self.jobs)
        for drive in list(self.known_drive_status):
            if drive not in drives:
                del self.known_drive_status[drive]
        self._update_drive_statuses(drives)
        self._update_run_button_state()

    def import_job_file_dialog(self):
        """File > Import Master Jobs Profile: replace the current job profiles with a JOB file from anywhere (e.g. a backup)."""
        if self._operation_is_running():
            messagebox.showinfo("Import Master Jobs Profile", "Please wait until the current operation finishes.", parent=self)
            return
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Import Master Jobs Profile",
            filetypes=[("EZee-Backup job files", "*.json"), ("All files", "*.*")],
        )
        if not chosen:
            return
        source = Path(chosen)
        target = job_file_path()
        if source.resolve() == target.resolve():
            messagebox.showinfo("Import Master Jobs Profile", "That file is already your current job file.", parent=self)
            return

        new_jobs, new_raw, problem = read_jobs_file(source)
        if new_jobs is None:
            messagebox.showerror(
                "Import Master Jobs Profile",
                f"This file cannot be imported because it is {problem}.\n\n{source}\n\n"
                "Your current job profiles have not been changed.",
                parent=self,
            )
            return
        current_jobs, current_raw, _problem = read_jobs_file(target)
        current_jobs = current_jobs or []
        if new_raw == current_raw:
            messagebox.showinfo("Import Master Jobs Profile", "That file is identical to your current job profiles.", parent=self)
            return

        groups = {str(job.get("group", "")).strip() for job in new_jobs} - {""}
        message = (
            f"Import {len(new_jobs)} job profile{'s' if len(new_jobs) != 1 else ''} "
            f"({len(groups)} group{'s' if len(groups) != 1 else ''}) from:\n{source}\n\n"
        )
        if current_jobs:
            message += (
                f"This replaces your current {len(current_jobs)} job profile{'s' if len(current_jobs) != 1 else ''}:\n"
                f"{summarize_job_changes(current_jobs, new_jobs).replace(' | ', chr(10))}\n\n"
                "Your current profiles will be kept as a dated copy, so you can undo this with "
                "Edit > Restore Master Jobs Profile from History."
            )
        else:
            message += "You have no job profiles at the moment, so nothing will be replaced."
        if getattr(self, "_profile_modified", False):
            message += "\n\nUnsaved changes to the current job will be lost."
        if not messagebox.askyesno("Import Master Jobs Profile", message, icon="warning" if current_jobs else "question", parent=self):
            return

        try:
            imported = import_job_file(target, source)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Import Master Jobs Profile", f"The import did not complete:\n{exc}", parent=self)
            return
        self._apply_replaced_jobs(imported, f"Imported {len(imported)} job profiles from {source}.")

    def _report_job_file_recovery(self, notice):
        log_name = integrity_log_path(job_file_path()).name
        self._log(f"JOB file problem: {notice}\nDetails are in {log_name}.", "job_report")
        messagebox.showwarning("JOB File Recovery", f"{notice}\n\nDetails are in {log_name}.", parent=self)

    def _mode_changed(self):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "job":
            index = int(selected[1])
            mode = self.mode_var.get()
            self.jobs[index]["mode"] = mode
            self._update_sidebar_job_mode(index, mode)
            self._set_profile_modified(True)

    def _update_sidebar_job_mode(self, index, mode):
        for item_id in self.job_tree.get_children(""):
            descendants = self.job_tree.get_children(item_id)
            for child_id in descendants:
                values = self.job_tree.item(child_id).get("values", ())
                if len(values) >= 2 and values[0] == "job" and int(values[1]) == index:
                    self.job_tree.item(child_id, tags=(mode,))

    def delete_current_job(self):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "group":
            return
        if not selected or selected[0] != "job":
            messagebox.showwarning("No job selected", "Select a job before deleting.")
            return
        index = int(selected[1])
        job = self.jobs[index]
        if not messagebox.askyesno("Delete Job", f"Delete job '{job.get('name', 'Untitled')}'?", parent=self):
            return
        self.jobs.pop(index)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list(collapsed=True)
        self._focus_job_in_sidebar(None)
        self._log(f"Deleted job: {job.get('name', 'Untitled')}")

    def load_selected_job(self, index=None):
        if index is None:
            selected = self._selected_sidebar_item()
            index = int(selected[1]) if selected and selected[0] == "job" else -1
        if index < 0:
            messagebox.showwarning("No job selected", "Select a job before loading.")
            return
        job = self.jobs[index]
        self._loading_job = True
        try:
            self.job_name.set(job.get("name", ""))
            self.source_var.set(job.get("source", ""))
            self.destination_var.set(job.get("destination", ""))
            self.include_subfolders_var.set(job.get("include_subfolders", True))
            saved_mode = job.get("mode", "backup")
            self.mode_var.set("move" if saved_mode == "transfer" else saved_mode)
            self.refresh_folder_views()
        finally:
            self._loading_job = False
        self._set_profile_modified(False)
        self._update_run_button_state()
        job_label = job.get('name', 'Unnamed')
        if self._last_selection_offline_drives:
            drives = ', '.join(self._last_selection_offline_drives)
            self._log(
                f"Loaded job: {job_label} - ⚠ Drive {drives} OFFLINE, this profile cannot run.",
                "job_report",
            )
        else:
            self._log(f"Loaded job: {job_label}")

    def add_job_to_group(self, index, x_root=None, y_root=None):
        job = self.jobs[index]
        group = self._select_group_for_job(job.get("group", ""), x_root, y_root)
        if not group or not group.strip():
            return
        job["group"] = group.strip()
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list(collapsed=True)
        self._focus_job_in_sidebar(index, job["group"])
        self._log(f"Added job '{job.get('name', 'Untitled')}' to group '{job['group']}'.")

    def duplicate_job(self, index):
        source_job = self.jobs[index]
        source_name = str(source_job.get("name", "Untitled"))
        duplicate_name = f"{source_name} Copy"
        suffix = 2
        existing_names = {str(job.get("name", "")).strip().casefold() for job in self.jobs}
        while duplicate_name.strip().casefold() in existing_names:
            duplicate_name = f"{source_name} Copy {suffix}"
            suffix += 1
        new_name = simpledialog.askstring("Duplicate Job", "New job name:", initialvalue=duplicate_name, parent=self)
        if not new_name or not new_name.strip():
            return
        duplicated_job = source_job.copy()
        duplicated_job["name"] = new_name.strip()
        self.jobs.insert(index + 1, duplicated_job)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Duplicated job '{source_name}' as '{duplicated_job['name']}'.")

    def _select_group_for_job(self, current_group="", x_root=None, y_root=None):
        groups = sorted({str(job.get("group", "")).strip() for job in self.jobs if str(job.get("group", "")).strip()})
        create_new_group = "Create New Group"
        choices = groups + [create_new_group]
        dialog = tk.Toplevel(self)
        dialog.title("Add to Group")
        dialog.configure(bg="#111827")
        dialog.resizable(False, False)
        dialog.transient(self)

        tk.Label(dialog, text="Choose a group:", bg="#111827", fg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(
            padx=18, pady=(16, 6), anchor="w"
        )
        group_var = tk.StringVar(value=current_group if current_group in groups else create_new_group)
        group_menu = ttk.Combobox(dialog, textvariable=group_var, values=choices, state="readonly", width=30)
        group_menu.pack(padx=18, pady=(0, 14))

        result = {"group": None}

        def confirm():
            selected_group = group_var.get()
            if selected_group == create_new_group:
                selected_group = simpledialog.askstring("Create New Group", "Group name:", parent=self)
            result["group"] = selected_group
            dialog.destroy()

        buttons = tk.Frame(dialog, bg="#111827")
        buttons.pack(fill="x", padx=18, pady=(0, 16))
        tk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy,
            bg="#1f2937",
            fg="#e2e8f0",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="right")
        tk.Button(
            buttons,
            text="Add",
            command=confirm,
            bg="#38bdf8",
            fg="#0f172a",
            activebackground="#7dd3fc",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="right", padx=(0, 8))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.update_idletasks()
        if x_root is not None and y_root is not None:
            dialog.geometry(f"+{int(x_root)}+{int(y_root)}")
        dialog.grab_set()
        self.wait_window(dialog)
        return result["group"]

    def remove_job_from_group(self, index):
        job = self.jobs[index]
        group = str(job.get("group", "")).strip()
        if not group:
            return
        job.pop("group", None)
        save_jobs(self.jobs, job_file_path())
        # An emptied group drops out of the tree, so everything simply stays closed.
        self.refresh_jobs_list(collapsed=True)
        self._focus_job_in_sidebar(None, group)
        self._log(f"Removed job '{job.get('name', 'Untitled')}' from group '{group}'.")

    def rename_sidebar_item(self, kind, value):
        if kind == "all":
            return
        if kind == "job":
            index = int(value)
            job = self.jobs[index]
            old_name = job.get("name", "Untitled")
            new_name = simpledialog.askstring("Rename Job", "New name:", initialvalue=old_name, parent=self)
            if not new_name or not new_name.strip():
                return
            new_name = new_name.strip()
            job["name"] = new_name
            if self._selected_sidebar_item() == ("job", value):
                self.job_name.set(new_name)
            log_message = f"Renamed job '{old_name}' to '{new_name}'."
        elif kind == "group":
            old_name = str(value)
            new_name = simpledialog.askstring("Rename Group", "New name:", initialvalue=old_name, parent=self)
            if not new_name or not new_name.strip():
                return
            new_name = new_name.strip()
            for job in self.jobs:
                if str(job.get("group", "")).strip() == old_name:
                    job["group"] = new_name
            log_message = f"Renamed group '{old_name}' to '{new_name}'."
        else:
            return
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(log_message)

    def delete_group(self, group_name):
        group_name = str(group_name).strip()
        if not group_name:
            return
        if not messagebox.askyesno(
            "Delete Group",
            f"Delete group '{group_name}'? Jobs in this group will be moved to All Jobs.",
            parent=self,
        ):
            return
        for job in self.jobs:
            if str(job.get("group", "")).strip() == group_name:
                job.pop("group", None)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Deleted group '{group_name}'.")

    def _jobs_for_selection(self):
        selected = self._selected_sidebar_item()
        if not selected:
            return []
        return jobs_for_sidebar_selection(self.jobs, selected[0], selected[1])

    def _run_next_job(self):
        if not self.pending_jobs:
            return
        job = self.pending_jobs.pop(0)
        self.batch_job_names.append(str(job.get("name", "Untitled")))
        self.source_var.set(job.get("source", ""))
        self.destination_var.set(job.get("destination", ""))
        self.include_subfolders_var.set(job.get("include_subfolders", True))
        self.mode_var.set("move" if job.get("mode", "backup") == "transfer" else job.get("mode", "backup"))
        self.job_name.set(job.get("name", ""))
        self.refresh_folder_views()
        self.run_backup(from_queue=True)

    def run_backup(self, from_queue=False):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "all" and not from_queue:
            messagebox.showinfo("Select a job or group", "Select an individual job or a group before running a backup.", parent=self)
            return
        selected_jobs = self._jobs_for_selection()
        if selected_jobs and not from_queue:
            self.pending_jobs = list(selected_jobs)
            self.batch_job_names = []
            self.batch_job_results = []
            self._run_next_job()
            return
        self.refresh_folder_views()

        source = self.source_var.get().strip()
        destination = self.destination_var.get().strip()
        if not has_valid_folder_pair(source, destination):
            play_error_sound()
            messagebox.showerror("Missing folders", "Please choose a source and destination folder.")
            return

        accessible, reason = paths_are_accessible(source, destination)
        if not accessible:
            play_error_sound()
            current_name = self.batch_job_names[-1] if self.batch_job_names else self.job_name.get() or "Untitled"
            self._log(f"ERROR: Skipped job '{current_name}' - {reason}", "job_report")
            messagebox.showerror("Drive Offline / Path Unavailable", reason, parent=self)
            if from_queue:
                self.batch_job_results.append((current_name, reason))
                if self.pending_jobs:
                    self.after_idle(self._run_next_job)
                else:
                    self._log_job_batch_report()
                    self.pending_jobs = []
            return

        mode = self.mode_var.get()
        log_mode = self.log_mode_var.get()
        verbose = log_mode == "Verbose"

        if mode == "move":
            confirmed = messagebox.askyesno(
                "Confirm Move Operation",
                "Move will remove each file from the source after it is copied successfully.\n\nDo you want to continue?",
                parent=self,
            )
            if not confirmed:
                self._log("Move operation cancelled.")
                return

        if mode == "twoway":
            confirmed = messagebox.askyesno(
                "Confirm Sync Operation",
                "Sync can delete files on the Source and/or Destination when it detects "
                "the file was removed on the other side since the last sync.\n\n"
                "Deleted files are sent to the Recycle Bin, not permanently erased.\n\n"
                "Do you want to continue?",
                parent=self,
            )
            if not confirmed:
                self._log("Sync operation cancelled.")
                return
            self._launch_sync_job(source, destination, self.include_subfolders_var.get(), log_mode)
            return

        command = build_robocopy_command(
            source,
            destination,
            mode,
            verbose=verbose,
            include_subfolders=self.include_subfolders_var.get(),
        )
        self._log(f"Running: {' '.join(command)}")

        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=False,
                creationflags=creationflags,
            )
            output_queue = queue.Queue()
            output_thread = threading.Thread(target=self._stream_process_output, args=(process, output_queue, log_mode), daemon=True)
            self.active_process = process
            self.process_paused = False
            self.operation_aborted = False
            self._set_operation_controls(True)
            self._start_destination_auto_refresh()
            output_thread.start()
            self.after(100, lambda: self._poll_process(process, output_thread, output_queue, "Operation complete with exit code {code}."))
        except FileNotFoundError:
            self._set_operation_controls(False)
            self._log("Robocopy was not found. This app requires a Windows system with ROBOCOPY available.")
            play_error_sound()
            messagebox.showerror("ROBOCOPY missing", "Robocopy is not available on this system.")
        except Exception as exc:
            self._set_operation_controls(False)
            self._log(f"Unexpected error: {exc}")
            play_error_sound()
            messagebox.showerror("Backup Failed", str(exc))


def main():
    app = EZeeBackupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
