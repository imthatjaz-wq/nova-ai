# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-08-20

## [0.2.1] - 2025-08-20

### Added
- Diagnostics: `nova diag --json` with filters, library versions, HTTP cache stats, rate limiter, and scheduler state
- Doctor: `nova doctor` runs health checks and suggests fixes
- Tooling: ruff, mypy, pre-commit hooks; CI runs pre-commit and pytest on PRs
- Packaging: version single-sourced; release workflow uploads artifacts and can publish to PyPI
- Windows: installer script; schedule/unschedule helpers (dry-run by default)
- Docs: Developing section, Troubleshooting tips, examples and scripts, demo GIF placeholder

### Changed
- CLI `diag` text output now reflects richer runtime info
- CI adds demo.gif size guard (≤ 2MB)

### Fixed
- Minor style and typing issues in CLI and tests

- Internet: multi-source aggregation (Wikipedia + search), citations in answers; jobs use aggregator
- Memory: tiny local embeddings + semantic search; nightly vectorization
- Knowledge Graph: relations schema/APIs; relation extraction during consolidation
- Security: strict host allowlist; red-team tests; elevated path checks validated
- Scheduler/UI: recurring schedules; health checks; CLI QoL commands (config, recent, clear, health)
- All tests green; offline-safe

## [0.1.0] - 2025-08-20

- Initial release.
- Local deterministic assistant with:
  - Permission gate (read-only by default), elevation whitelist, audit logs
  - Ethical internet (allowlists, SafeSearch, rate limiting); tests fully offline
  - Memory (STM/LTM SQLite) with consolidation and background jobs
  - CLI commands: hello, version, chat, jobs research/nightly, diag
  - Minimal in-process scheduler; Windows-first path normalization
- Packaging: pyproject with console script `nova`; editable install supported

See `RELEASE_NOTES.md` for highlights and upgrade notes.
