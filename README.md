# Nova (Local AI Assistant)

Nova is a local, deterministic AI assistant that runs on Windows in C:\\Nova. She has read-only access by default, with a permission gate for any write/modify actions. Internet access is ethical and minimal, with SafeSearch/allowlists and full audit logs.

This repo follows a staged build plan through Segment 10. It includes configuration, logging, permissions, memory, internet module, conversation core, commands, UI/CLI, background jobs, and tests.

## Quickstart

1. Python 3.10+ recommended
2. (Optional) Create and activate a virtual environment
3. Install dependencies
4. Run the tests and CLI help

```powershell
# in C:\Nova
python -m pip install --upgrade pip
python -m pip install -e .
pytest -q
nova --help
nova version
```

pipx install (optional):

```powershell
pipx install .
# then the console script 'nova' should be on PATH
nova --help
```

Demo:

![Nova demo](docs/examples/demo.gif)

Notes:
- Logs go to `C:\Nova\data\logs` by default (created at runtime if possible).
- Configure via environment variables or `.env` (see `.env.example`).
- Do not use external LLM APIs; all logic is deterministic or locally trained.
- For CI/non-interactive runs, set `NOVA_NONINTERACTIVE=1` and control prompts with `NOVA_PERMISSION_DEFAULT=deny|allow|prompt`.

## Project layout

- `nova_core.py` — entry integration (wired in later segments)
- `nova/` — core utilities, config, logging, permissions (stub), scheduler (stub)
- `conversation/` — NLU/NLG/dialogue (stubs for now)
- `memory/` — STM/LTM/indexing/consolidation (stubs for now)
- `internet/` — search/fetch/summarize (stubs for now)
- `commands/` — registry/handlers (stubs for now)
- `workspace/` — bus/self-model/affect (stubs for now)
- `ui/` — CLI (Typer-based). Commands: `hello`, `version`, `chat`, `jobs research`, `jobs nightly`, `diag`.
- `security/` — admin helper + policies (stubs for now)
- `tests/` — pytest-based tests
- `data/` — runtime artifacts (logs, db)

See `docs/NovaPlan.md` for the canonical specification. A helper `Bootstrap.ps1` is provided for quick setup on Windows.

## Release checklist and policy

Version is single-sourced in `nova/__init__.py` (`__version__`). `pyproject.toml` reads it dynamically.

Policy:
- Use SemVer (MAJOR.MINOR.PATCH).
- Document each release in `CHANGELOG.md` (Added/Changed/Fixed).
- CI will fail if the version changes without a CHANGELOG entry.

Checklist:
- [ ] Update `nova/__init__.py` `__version__`
- [ ] Update `CHANGELOG.md`
- [ ] Run `pytest -q` — ensure all tests pass
- [ ] `pip install -e .` sanity check; `nova --help` and `nova version` work
- [ ] Tag release (e.g., `v0.2.1`)
- [ ] Build and publish artifacts (see CI release workflow)

## How to verify (smoke tests)

- Set environment for noninteractive tests:
	- `NOVA_NONINTERACTIVE=1` and `NOVA_PERMISSION_DEFAULT=allow`
- Run `pytest -q` — all tests pass, no network required
- CLI sanity:
	- `nova --help`, `nova version`, `nova hello`
	- `nova chat --once "hello"` prints a response
	- `nova jobs nightly` prints "Nightly consolidation complete"
	- `nova jobs research --max-items 1` prints "Researched X gap(s)."
- Logs: after any CLI call, `C:\Nova\data\logs\nova.log` exists (if permission allowed)

## Windows Task Scheduler

- Preview the scheduled task creation (dry-run):
	- `nova jobs schedule --time 02:00`
- Apply it (creates a Windows Scheduled Task named NovaNightly):
	- `nova jobs schedule --time 02:00 --apply`
- Remove it:
	- `nova jobs unschedule --apply`

Optional: use `scripts/Install-Nova.ps1` to set up a venv, install the package, and schedule the nightly task (dry-run by default; pass `-Apply` to execute).

## Developing

Install dev dependencies and pre-commit hooks, then run checks locally:

```powershell
# in C:\Nova
python -m pip install --upgrade pip
pip install -e .[dev]
pre-commit install
pre-commit run --all-files
pytest -q
```

Diagnostics and health during development:

```powershell
# Human-readable
python -m ui.cli diag

# JSON for tooling or quick inspection
python -m ui.cli diag --json
```

Common fields include versions of key libraries, HTTP cache size/TTL, rate limiter state, and scheduler job counts. Set `NOVA_NONINTERACTIVE=1` for deterministic runs.

## Examples

- PowerShell helpers in `scripts/`:
	- `scripts/run-chat-once.ps1` — runs a single chat turn with default input "hello".
	- `scripts/run-daily-summary.ps1` — runs the daily summary job.
- Sample outputs in `docs/examples/`:
	- `docs/examples/transcript-chat-once.txt` — minimal chat transcript.
	- `docs/examples/output-daily-summary.txt` — idle daily digest sample.
