# Changelog

All notable changes to this project will be documented in this file.

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
