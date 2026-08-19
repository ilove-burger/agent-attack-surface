# Codex — coverage detail

Status legend in the [root README](../README.md). Reproductions use the `hunma_agent` harness against
pinned `@openai/codex` artifacts (SHA-256 in `harness/versions/manifest.json`).

## Verified here

| ID | Surface | Verdict | Harness |
|---|---|---|---|
| [CVE-2025-61260](cve-2025-61260-env-codexhome/) | project `.env` re-points `CODEX_HOME` → local MCP auto-spawn | reproduced across vuln/fixed/current | `compare-codex-61260` (+ `-variants`) |

## Open / candidate angles

New Codex angles are probed on top of the CVE-2025-61260 harness (config-reload, gitdir/commondir,
nested/symlink/worktree repos, session-resume, pre-existing CODEX_HOME negative control). See the
`compare-codex-61260-variants` case matrix in `hunma_agent`. No novel Codex finding promoted yet.
