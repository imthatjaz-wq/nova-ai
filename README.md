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

## Release checklist (minimal)

- [ ] Update version in `pyproject.toml` and `nova/__init__.py`
- [ ] Run `pytest -q` — ensure all tests pass
- [ ] `pip install -e .` sanity check and `nova --help` works
- [ ] Review README and CLI help for accuracy
- [ ] Tag release and publish wheel/sdist if desired

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
