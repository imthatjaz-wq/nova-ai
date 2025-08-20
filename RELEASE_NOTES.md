# Release Notes — Nova v0.1.0

Date: 2025-08-20

Highlights
- Local, deterministic assistant with strict permission gate and audit logging
- Ethical internet module (allowlists, SafeSearch, rate limiting); tests are offline
- Memory (STM/LTM SQLite) with consolidation and background jobs (research + nightly)
- CLI with chat, jobs research/nightly, hello, version
- Minimal in-process scheduler; Windows-first path/elevation policies

Breaking changes
- None (initial release)

Known limitations
- Internet search requires a Bing API key for live queries; tests use mocks
- Writes are dry-run by default unless explicitly allowed; elevated operations are whitelisted

Upgrade notes
- Install with `pip install -e .`; run `pytest -q` to validate
- Configure `.env` using the provided `.env.example`

Planned for v0.2.0
- Richer NLU intents and entities; small ML intent classifier (local, deterministic)
- Persistence toggles and clearer consent flows for LTM and logs
- Scheduled nightly job via Windows Task Scheduler optional integration
- CLI improvements: `nova diag` extended, `nova logs` helper
- CI workflows for tests and wheels on Windows matrix
