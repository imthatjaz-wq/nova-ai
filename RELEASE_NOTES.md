# Release Notes — Nova v0.2.0

Date: 2025-08-20

Highlights
- Multi-source internet aggregation with citations in dialogue and jobs
- Semantic memory: tiny local embeddings + semantic query fallback; nightly vector refresh
- Knowledge graph: relations schema/APIs + extraction (e.g., capital_of)
- Policy hardening: strict host allowlist; elevation checks + red-team tests
- Scheduler/UI: recurring scheduler, health checks, and new CLI QoL commands

Breaking changes
- None (backward-compatible improvements)

Known limitations
- Live internet search requires a Bing API key; tests use mocked HTTP
- Writes are permission-gated; operations outside C:\Nova\data are treated as elevated (dry-run in CLI)

Upgrade notes
- `pip install -e .` to update; run `pytest -q` to validate locally
- Review `.env` for search provider, allowlist, and noninteractive settings

Next
- Phase 8 packaging tasks continue: tagged releases and distribution automation
- CLI improvements: `nova diag` extended, `nova logs` helper
- CI workflows for tests and wheels on Windows matrix
