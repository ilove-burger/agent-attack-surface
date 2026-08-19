# agent-attack-surface

Shared **coverage map** for our whitehat research on AI coding agents — **Claude Code** (Anthropic)
and **Codex** (OpenAI). Scope: **coordinated disclosure** (HackerOne Anthropic / OpenAI Codex).
This repo is the *index* of what's been probed and the verdict for each surface, so teammates don't
re-plough the same ground. The runnable proof lives in the **`hunma_agent`** harness (marker-only,
bwrap-isolated, mock Anthropic API, real Claude Code / Codex artifacts); each folder links to the
exact `compare-*` script.

> **Private repo.** Some surfaces touch unfixed or disclosure-pending issues. Do not make public or
> redistribute. No live weaponization (reverse shells, hostile artifacts) is committed here.

## Legend

- 🟢 **KILLED** — probed and defended; the attack yields no privilege. Not submittable. (Full writeup + reproducible harness here.)
- 🔴 **LIVE** — confirmed exploitable; disclosure in progress.
- 🟡 **INFO** — works but likely "intended / documented"; low severity.
- ⚪ **PATCHED** — was live in an old version, fixed upstream.
- ↗ **EXTERNAL** — inherited from a teammate's workspace; **not independently re-verified here** (pointer only).
- ☐ **OPEN** — not yet investigated.

## Claude Code

| ID | Surface | Status | Verified here | Detail |
|---|---|---|---|---|
| A02 / P4 | WebFetch content → IPI → Bash | 🟢 KILLED | ✅ 1.0.92·2.1.226·2.1.235 | [claudecode/a02-webfetch-ipi](claudecode/a02-webfetch-ipi/) |
| A03 / P2 | Malicious MCP server forges `tool_use` in `tool_result` | 🟢 KILLED | ✅ 2.1.226·2.1.235 (+1.0.92 source) | [claudecode/a03-mcp-forged-tooluse](claudecode/a03-mcp-forged-tooluse/) |
| A11 / P3 | Malicious `CLAUDE.md` auto-discovery → IPI → Bash | 🟢 KILLED | ✅ 1.0.92·2.1.226·2.1.235 | [claudecode/a11-claudemd-ipi](claudecode/a11-claudemd-ipi/) |
| A14 | Bash **LLM** prefix-classifier prompt injection | 🟢 KILLED | ✅ 1.0.92·2.1.226·2.1.235 (surface removed in 2.1.235) | [claudecode/a14-llm-classifier-ipi](claudecode/a14-llm-classifier-ipi/) |
| A10 | Skill inline shell × **code** Bash-classifier bypass | 🟢 KILLED | ↗ external (malhyuk) | — pointer only |
| A01 | `claude-cli://` deep-link `--settings` reinjection | ⚪ PATCHED | ↗ external (malhyuk) | — pointer only |
| A04 | NM7 helper exec via non-interactive trust bypass | 🟡 INFO | ↗ external (malhyuk) | — pointer only |
| A12 | Pre-trust RCE via `.git/config` `core.fsmonitor` | 🔴 LIVE? (disclosure/dup pending) | ↗ external (malhyuk) | **excluded** — sensitive live PoC; tracked in malhyuk's workspace |
| A05 | `--plugin-url` arbitrary zip → execution | ☐ OPEN | — | — |
| A08 | Trust-inheritance via parent path | ☐ OPEN | — | — |
| A13 | OAuth callback param injection | ☐ OPEN | — | — |

**Common pattern across the four KILLs (A02/A03/A11/A14):** the load-bearing control is a *structural*
code-layer invariant — content-type whitelist on MCP results, provenance (a `tool_use` is honored
only from the assistant turn), and rule-match/AST permission. The foolable LLM / data / context / web
layers are **non-load-bearing**: even a maximally-successful injection grants zero privilege because
the permission layer denies the induced command independently.

## Codex

| ID | Surface | Status | Verified here | Detail |
|---|---|---|---|---|
| CVE-2025-61260 | project `.env` re-points `CODEX_HOME` → local MCP spawn | 🟢 reproduced (3-tier) | ✅ 0.21.0 vuln / 0.22.0 fixed / 0.147.0 current | [codex/cve-2025-61260-env-codexhome](codex/cve-2025-61260-env-codexhome/) |

## How to reproduce

Every 🟢 here is a deterministic run in the **`hunma_agent`** harness. Clone it next to this repo:

```
git clone <hunma_agent remote>
cd hunma_agent && ./harness/compare-claude-p4 --repeat 2   # (or -a14 / -p2 / -p3 / compare-codex-61260)
```

The harness fetches/uses pinned artifacts by SHA-256 (see `harness/versions/manifest.json`), runs the
real CLI under bwrap against a loopback mock Anthropic API, and asserts a marker-only oracle
(a `touch marker` fires only if the attack actually gained execution). Each folder's **Files** section
names the exact fixtures and cases.
