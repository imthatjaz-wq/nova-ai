"""Command handlers with write-gated operations."""
from __future__ import annotations

from pathlib import Path
from nova.permissions import request_permission, Decision, interactive_prompt
from security import policies
from nova import scheduler
import os
import shutil

def open_url(url: str) -> str:
    # No side-effects in Segment 1
    return f"[dry-run] Would open URL: {url}"


def create_file(path: str, content: str = "") -> str:
    p = Path(path)
    decision = request_permission(action="create file", resource=str(p), path=p)
    if decision is not Decision.APPROVED:
        return f"[denied] create_file {p}"
    # If approved but outside data dir, still do a dry-run for Segment 2; real write later
    if policies.requires_elevation_for_path(p):
        return f"[approved] Would create (elev needed) {p}"
    return f"[approved] Would create {p}"


def open_app(name: str) -> str:
    # Dry-run: verify the app exists in PATH
    exe = shutil.which(name)
    if exe:
        return f"[dry-run] Would open app: {name} ({exe})"
    return f"[error] app not found: {name}"


def set_reminder(seconds: int, message: str) -> str:
    scheduler.schedule_once(seconds, lambda: scheduler.alert(message))
    return f"[scheduled] in {seconds}s: {message}"


def search_local_files(root: str, pattern: str) -> str:
    # Read-only file search; no writes
    r = Path(root)
    if not r.exists() or not r.is_dir():
        return f"[error] root not found: {root}"
    matches = []
    try:
        for p in r.rglob(pattern):
            if p.is_file():
                matches.append(str(p))
    except Exception:
        return f"[error] search failed under: {root}"
    if not matches:
        return "[ok] no matches"
    return "\n".join(matches[:20])


def show_logs() -> str:
    logs_dir = policies.get_data_dir() / "logs"
    if not logs_dir.exists():
        return f"[ok] logs dir not present: {logs_dir}"
    files = list(logs_dir.glob("*.log"))
    if not files:
        return "[ok] no log files"
    return "\n".join(str(f) for f in files)


def open_file(path: str) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return f"[error] file not found: {p}"
    return f"[dry-run] Would open file: {p}"


def copy_file(src: str, dst: str) -> str:
    s = Path(src)
    d = Path(dst)
    if not s.exists() or not s.is_file():
        return f"[error] source not found: {s}"
    decision = request_permission(action="copy file", resource=f"{s} -> {d}", path=d)
    if decision is not Decision.APPROVED:
        return f"[denied] copy_file {s} -> {d}"
    if policies.requires_elevation_for_path(d):
        return f"[approved] Would copy (elev needed) {s} -> {d}"
    return f"[approved] Would copy {s} -> {d}"


def move_file(src: str, dst: str) -> str:
    s = Path(src)
    d = Path(dst)
    if not s.exists() or not s.is_file():
        return f"[error] source not found: {s}"
    decision = request_permission(action="move file", resource=f"{s} -> {d}", path=d)
    if decision is not Decision.APPROVED:
        return f"[denied] move_file {s} -> {d}"
    if policies.requires_elevation_for_path(d):
        return f"[approved] Would move (elev needed) {s} -> {d}"
    return f"[approved] Would move {s} -> {d}"


def delete_file(path: str) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return f"[error] file not found: {p}"
    decision = request_permission(action="delete file", resource=str(p), path=p)
    if decision is not Decision.APPROVED:
        return f"[denied] delete_file {p}"
    # Double-confirm destructive action
    noninteractive = os.getenv("NOVA_NONINTERACTIVE", "0").lower() in ("1", "true", "yes")
    if noninteractive:
        return f"[cancelled] delete_file {p}"
    sure = interactive_prompt(f"Confirm delete {p}?", default=False)
    if not sure:
        return f"[cancelled] delete_file {p}"
    if policies.requires_elevation_for_path(p):
        return f"[approved] Would delete (elev needed) {p}"
    return f"[approved] Would delete {p}"
