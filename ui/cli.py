from __future__ import annotations
from importlib.metadata import version, PackageNotFoundError
import os
from pathlib import Path
import typer
from colorama import Fore, Style, init as colorama_init
from typing import Any

from nova.config import Settings
from nova.logging_setup import setup_logging
from conversation.dialogue_manager import DialogueManager
from nova.jobs import run_gap_research, run_nightly, run_daily_summary
from nova.jobs import run_health_checks
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
def chat(
    once: str = typer.Option(None, help="If provided, handle a single input and exit"),
    verbose: bool = typer.Option(False, help="Include internal trace in replies"),
) -> None:
    """Chat REPL. Use --once for a single turn (good for tests)."""
    dm = DialogueManager()
    dm.verbose = verbose
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


@jobs_app.command("daily-summary")
def jobs_daily_summary() -> None:
    """Generate and store today's daily digest from inbox/learning/chats."""
    ltm = LTM()
    digest = run_daily_summary(ltm)
    print(digest or "Daily digest: idle")


@jobs_app.command("status")
def jobs_status() -> None:
    """Show last job runs (nightly, research, daily-summary)."""
    ltm = LTM()
    rows = ltm.get_events("job")[:20]
    if not rows:
        print("No job runs yet.")
        return
    # Parse and colorize
    from colorama import Fore, Style
    def fmt(row: tuple[int, str, str, str]) -> str:
        _id, _typ, content, ts = row
        status = "ok" if " status=ok" in content else ("fail" if " status=fail" in content else "?")
        color = Fore.GREEN if status == "ok" else (Fore.RED if status == "fail" else Fore.YELLOW)
        return f"{color}{ts} {content}{Style.RESET_ALL}"
    for r in rows:
        print(fmt(r))


app.add_typer(jobs_app, name="jobs")


@jobs_app.command("schedule")
def jobs_schedule(
    task_name: str = typer.Option("NovaNightly", help="Windows Task name"),
    time: str = typer.Option("02:00", help="Daily start time HH:MM in 24h"),
    apply: bool = typer.Option(False, help="Apply the change (otherwise dry-run)"),
) -> None:
    """On Windows, create a daily scheduled task to run nightly consolidation."""
    from nova.windows import is_windows
    if not is_windows():
        print("[error] Windows-only command")
        raise typer.Exit(code=1)
    from pathlib import Path
    from nova.windows import build_schtasks_create
    workdir = Path(__file__).resolve().parents[1]
    cmd = build_schtasks_create(task_name=task_name, working_dir=workdir, time_hhmm=time)
    if not apply:
        print("[dry-run] " + " ".join(cmd))
        return
    import subprocess
    # Permission gate before making system changes
    from nova.permissions import request_permission, Decision
    perm = request_permission(action="schedule task", resource=task_name, path=None)
    if perm is not Decision.APPROVED:
        print(f"[denied] schedule {task_name}")
        raise typer.Exit(code=1)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if proc.returncode != 0:
            print("[error] schtasks failed:\n" + proc.stdout + proc.stderr)
            raise typer.Exit(code=proc.returncode)
        print(f"[ok] Scheduled task '{task_name}' at {time}")
    except FileNotFoundError:
        print("[error] 'schtasks' not found; ensure you're on Windows")
        raise typer.Exit(code=1)


@jobs_app.command("unschedule")
def jobs_unschedule(
    task_name: str = typer.Option("NovaNightly", help="Windows Task name"),
    apply: bool = typer.Option(False, help="Apply the change (otherwise dry-run)"),
) -> None:
    """On Windows, delete the scheduled task created by 'jobs schedule'."""
    from nova.windows import is_windows
    if not is_windows():
        print("[error] Windows-only command")
        raise typer.Exit(code=1)
    from nova.windows import build_schtasks_delete
    cmd = build_schtasks_delete(task_name)
    if not apply:
        print("[dry-run] " + " ".join(cmd))
        return
    import subprocess
    from nova.permissions import request_permission, Decision
    perm = request_permission(action="unschedule task", resource=task_name, path=None)
    if perm is not Decision.APPROVED:
        print(f"[denied] unschedule {task_name}")
        raise typer.Exit(code=1)
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if proc.returncode != 0:
        print("[error] schtasks delete failed:\n" + proc.stdout + proc.stderr)
        raise typer.Exit(code=proc.returncode)
    print(f"[ok] Deleted task '{task_name}'")


@app.command("diag")
def diag(
    json: bool = typer.Option(False, "--json", help="Output diagnostics as JSON"),
    filter: list[str] = typer.Option(None, "--filter", help="Select top-level keys to output (JSON mode)"),
) -> None:
    """Print a quick diagnostic: env, paths, search config, and policy info."""
    settings = Settings()
    try:
        v = version("nova-assistant")
    except PackageNotFoundError:
        from nova import __version__ as v
    api_key_status = "set" if (settings.search_api_key or "") else "not set"
    info: dict[str, Any] = {
        "version": v,
        "env": settings.env,
        "data_dir": str(settings.data_dir),
        "logs_dir": str(settings.logs_dir),
        "logs_dir_exists": settings.logs_dir.exists(),
        "search_provider": settings.search_provider,
        "api_key": api_key_status,
        "domain_allowlist": settings.domain_allowlist,
        "http_rate_limit_per_min": settings.http_rate_limit_per_min,
    }
    # Library versions
    try:
        from importlib.metadata import version as _dist_version
        info["libs"] = {
            "requests": _dist_version('requests'),
            "typer": _dist_version('typer'),
            "colorama": _dist_version('colorama'),
        }
    except Exception:
        info["libs"] = {}
    # Policy sample
    dd = policies.get_data_dir()
    outside = Path("C:/Windows/Temp/nova_test.txt")
    info["policy"] = {
        "data_dir": str(dd),
        "data_dir_no_elevation": policies.requires_elevation_for_path(dd) is False,
        "outside_requires_elevation": bool(policies.requires_elevation_for_path(outside)),
    }
    # Prompt mode
    nonint = os.getenv("NOVA_NONINTERACTIVE", "0")
    perm_default = os.getenv("NOVA_PERMISSION_DEFAULT", "prompt")
    info["prompt_mode"] = {
        "noninteractive": nonint,
        "permission_default": perm_default,
    }
    # HTTP cache & scheduler
    try:
        from internet.fetch import _CACHE as _HTTP_CACHE
        from internet.fetch import _CACHE_TTL_SECONDS as _TTL
        from internet.fetch import get_rate_limiter
        from nova.scheduler import list_scheduled
        # Estimate cache size in bytes
        cache_bytes = sum(len(v[1].encode('utf-8')) for v in _HTTP_CACHE.values())
        rl = get_rate_limiter(settings)
        # Top 3 hosts by request count in current window
        host_counts = sorted(((h, c) for h, (_w, c) in rl.state.items()), key=lambda x: x[1], reverse=True)[:3]
        total_in_window = sum(c for (_w, c) in rl.state.values()) if rl.state else 0
        info["http"] = {
            "cache_entries": len(_HTTP_CACHE),
            "cache_ttl_seconds": _TTL,
            "cache_size_bytes": cache_bytes,
            "ratelimiter_hosts": len(rl.state),
            "ratelimiter_total_in_window": int(total_in_window),
            "ratelimiter_top_hosts": host_counts,
        }
        sch = list_scheduled()
        info["scheduler"] = {"scheduled_jobs": len(sch)}
    except Exception:
        info["http"] = {}
        info["scheduler"] = {}

    if json:
        import json as _json
        keys: list[str] = []
        if filter:
            # support comma-separated --filter "a,b"
            for f in filter:
                keys.extend([p.strip() for p in f.split(',') if p.strip()])
        if keys:
            filtered = {k: info.get(k) for k in keys if k in info}
            print(_json.dumps(filtered, indent=2, sort_keys=True))
        else:
            print(_json.dumps(info, indent=2, sort_keys=True))
        return

    # Text output fallback
    print("=== Nova Diagnostics ===")
    print(f"Version: {info['version']}")
    print(f"Env: {info['env']}")
    print(f"Data dir: {info['data_dir']}")
    print(f"Logs dir: {info['logs_dir']} (exists={info['logs_dir_exists']})")
    print(f"Search provider: {info['search_provider']}")
    print(f"API key: {info['api_key']}")
    print(f"Domain allowlist: {info['domain_allowlist']}")
    print(f"HTTP rate limit/min: {info['http_rate_limit_per_min']}")
    libs = info.get("libs", {}) or {}
    if isinstance(libs, dict) and libs:
        print("Libs: " + " ".join([f"{k}={v}" for k, v in libs.items()]))
    pol = info.get("policy", {}) or {}
    if isinstance(pol, dict) and pol:
        print(f"Policy: data dir={pol.get('data_dir')} no elevation={pol.get('data_dir_no_elevation')}")
        print(f"Policy: outside path requires elevation={pol.get('outside_requires_elevation')}")
    pm = info.get("prompt_mode", {}) or {}
    if isinstance(pm, dict) and pm:
        print(f"Noninteractive={pm.get('noninteractive')} PermissionDefault={pm.get('permission_default')}")
    http = info.get("http", {}) or {}
    if isinstance(http, dict) and http:
        print(f"HTTP cache entries: {http.get('cache_entries', 0)} TTL={http.get('cache_ttl_seconds', 0)}s")
        hosts = http.get('ratelimiter_hosts', 0)
        total = http.get('ratelimiter_total_in_window', 0)
        print(
            "RateLimiter: "
            f"hosts={hosts} "
            f"total_requests_in_window={total}"
        )
    sched = info.get("scheduler", {}) or {}
    if isinstance(sched, dict) and sched:
        print(f"Scheduled jobs: {sched.get('scheduled_jobs', 0)}")


@app.command("config")
def show_config() -> None:
    """Show current configuration values."""
    s = Settings()
    fields = [
        ("env", s.env),
        ("data_dir", s.data_dir),
        ("logs_dir", s.logs_dir),
        ("search_provider", s.search_provider),
        ("safesearch", s.safesearch),
        ("domain_allowlist", s.domain_allowlist),
    ]
    for k, v in fields:
        print(f"{k}: {v}")


@app.command("recent")
def recent_chats(limit: int = typer.Option(5, help="How many recent chats to show")) -> None:
    """Show recent chat events from memory (best-effort)."""
    ltm = LTM()
    rows = ltm.get_events("chat")[:limit]
    if not rows:
        print("No recent chats.")
        return
    for _id, _typ, content, ts in rows:
        print(f"[{ts}] {content}")


@app.command("clear")
def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


@app.command("health")
def health() -> None:
    """Run quick health checks and print result."""
    count = run_health_checks()
    print(f"Health checks passed: {count}")


@app.command("doctor")
def doctor() -> None:
    """Run health checks and print suggested fixes for common issues."""
    count = run_health_checks()
    print(f"Doctor report: {count}/3 checks passed")
    print("Suggested checks/fixes:")
    print(
        "- Permissions: set NOVA_NONINTERACTIVE=1 for CI; control prompts with "
        "NOVA_PERMISSION_DEFAULT=allow|deny|prompt"
    )
    print(
        "- Logging: ensure data/logs directory can be created (permission gate allows) and that "
        "nova.log exists after running any command"
    )
    print("- Policy: data dir shouldn't require elevation; outside paths should (see 'nova diag' policy lines)")
    print("- Install: run 'pip install -e .' and verify 'nova --help' works (console script installed)")
    print("- Network: configure search provider/key if needed; check 'nova diag' HTTP and rate limiter stats")

if __name__ == "__main__":
    # Allow `python -m ui.cli --help`
    app()
