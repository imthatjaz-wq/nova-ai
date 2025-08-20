from __future__ import annotations

import sys
from importlib.metadata import version, PackageNotFoundError
import os
from pathlib import Path
import typer
from colorama import Fore, Style, init as colorama_init

from nova.config import Settings
from nova.logging_setup import setup_logging
from conversation.dialogue_manager import DialogueManager
from nova.jobs import run_gap_research, run_nightly
from memory.store import LTM
from nova.permissions import request_permission, Decision
from security import policies

app = typer.Typer(add_completion=False, help="Nova CLI — local deterministic assistant")
jobs_app = typer.Typer(help="Background jobs: learning and consolidation")


@app.callback()
def main_callback() -> None:
    """Initialize color and logging early."""
    colorama_init(autoreset=True)
    settings = Settings()
    # Bootstrap runtime directories with permission gate
    try:
        data_dir: Path = settings.data_dir
        logs_dir: Path = settings.logs_dir
        approved = request_permission(
            action="create runtime directories",
            resource=str(logs_dir),
            path=logs_dir,
        )
        if approved is Decision.APPROVED:
            try:
                os.makedirs(data_dir, exist_ok=True)
                os.makedirs(logs_dir, exist_ok=True)
            except Exception:
                pass
    except Exception:
        pass
    setup_logging(settings)


@app.command()
def hello(name: str = "world") -> None:
    """Simple hello to validate CLI wiring."""
    print(Fore.CYAN + f"Hello, {name}!" + Style.RESET_ALL)


@app.command("version")
def version_cmd() -> None:
    """Print version info from package metadata."""
    try:
        v = version("nova-assistant")
    except PackageNotFoundError:
        from nova import __version__ as v  # fallback in editable/dev mode
    print(f"Nova v{v}")


@app.command()
def chat(once: str = typer.Option(None, help="If provided, handle a single input and exit")) -> None:
    """Chat REPL. Use --once for a single turn (good for tests)."""
    dm = DialogueManager()
    if once is not None:
        resp = dm.handle(once)
        # best-effort transcript logging (will be in-memory if denied)
        try:
            ltm = dm.ensure_ltm()
            ltm.log_event("chat", f"user: {once} | nova: {resp}")
        except Exception:
            pass
        print(Fore.GREEN + "Nova> " + Style.RESET_ALL + resp)
        return

    print(Fore.GREEN + "Nova> " + Style.RESET_ALL + "Hi! Type 'exit' to quit.")
    while True:
        try:
            user = input(Fore.YELLOW + "You> " + Style.RESET_ALL)
        except EOFError:
            break
        if user.strip().lower() in ("exit", "quit"):
            break
        resp = dm.handle(user)
        try:
            ltm = dm.ensure_ltm()
            ltm.log_event("chat", f"user: {user} | nova: {resp}")
        except Exception:
            pass
        print(Fore.GREEN + "Nova> " + Style.RESET_ALL + resp)


@jobs_app.command("research")
def jobs_research(max_items: int = typer.Option(3, help="Max gaps to research")) -> None:
    """Run gap research based on recent chats (saves notes with sources)."""
    ltm = LTM()
    count = run_gap_research(ltm, max_items=max_items)
    print(f"Researched {count} gap(s).")


@jobs_app.command("nightly")
def jobs_nightly() -> None:
    """Run nightly consolidation job."""
    ltm = LTM()
    run_nightly(ltm)
    print("Nightly consolidation complete.")


app.add_typer(jobs_app, name="jobs")


@app.command("diag")
def diag() -> None:
    """Print a quick diagnostic: env, paths, search config, and policy info."""
    settings = Settings()
    try:
        v = version("nova-assistant")
    except PackageNotFoundError:
        from nova import __version__ as v
    api_key_status = "set" if (settings.search_api_key or "") else "not set"
    print("=== Nova Diagnostics ===")
    print(f"Version: {v}")
    print(f"Env: {settings.env}")
    print(f"Data dir: {settings.data_dir}")
    print(f"Logs dir: {settings.logs_dir} (exists={settings.logs_dir.exists()})")
    print(f"Search provider: {settings.search_provider}")
    print(f"API key: {api_key_status}")
    print(f"Domain allowlist: {settings.domain_allowlist}")
    print(f"HTTP rate limit/min: {settings.http_rate_limit_per_min}")
    # Policy sample
    dd = policies.get_data_dir()
    outside = Path("C:/Windows/Temp/nova_test.txt")
    print(f"Policy: data dir={dd} no elevation={policies.requires_elevation_for_path(dd) is False}")
    print(f"Policy: outside path requires elevation={policies.requires_elevation_for_path(outside)}")
    # Prompt mode
    nonint = os.getenv("NOVA_NONINTERACTIVE", "0")
    perm_default = os.getenv("NOVA_PERMISSION_DEFAULT", "prompt")
    print(f"Noninteractive={nonint} PermissionDefault={perm_default}")

if __name__ == "__main__":
    # Allow `python -m ui.cli --help`
    app()
