# Claude Code — coverage detail

Status legend in the [root README](../README.md). "Verified here" = independently reproduced in this
workspace with the `hunma_agent` marker-only harness against real Claude Code artifacts (npm
`@anthropic-ai/claude-code[-linux-x64]` 1.0.92 / 2.1.226 / 2.1.235, pinned by SHA-256).

## Verified here (full writeup + harness)

| ID | Surface | Verdict | Harness |
|---|---|---|---|
| [A02 / P4](a02-webfetch-ipi/) | WebFetch content → IPI → Bash | KILLED | `compare-claude-p4` |
| [A03 / P2](a03-mcp-forged-tooluse/) | MCP server forges `tool_use` in `tool_result` | KILLED | `compare-claude-p2` |
| [A11 / P3](a11-claudemd-ipi/) | Malicious `CLAUDE.md` → IPI → Bash | KILLED | `compare-claude-p3` |
| [A14](a14-llm-classifier-ipi/) | Bash LLM prefix-classifier prompt injection | KILLED (surface removed in 2.1.235) | `compare-claude-a14` |

Each of the four confirms the same invariant from a different untrusted-content source: **the
injectable layer cannot grant tool permission.** The harness delivers the injection to the *maximum*
(forged block delivered / model fully "persuaded" / web page really fetched and its injection reaches
the main agent) and still observes the induced Bash **denied** (or the forged block dropped), while a
positive control with a real allow-rule fires the marker.

## Inherited / external (not re-verified here — pointer only)

These came from a teammate's (malhyuk) offensive workspace and are **not** independently reproduced in
this repo. Listed for coverage completeness; ask the original author for artifacts.

| ID | Surface | Reported status | Note |
|---|---|---|---|
| A10 | Skill inline shell × code Bash-classifier bypass (ANSI-C / process-sub / brace / Unicode / docker) | KILLED | tree-sitter code classifier robust; A14 is its LLM-layer follow-up (verified here) |
| A01 | `claude-cli://open?q=--settings=…` reinjection | PATCHED (≤2.1.117) | fixed upstream |
| A04 | NM7 helper exec via non-interactive (`T6()`) trust bypass | INFORMATIONAL | likely "documented `--print` behavior" |
| A12 | Pre-trust RCE via `.git/config` `core.fsmonitor` (git startup probe) | **CRITICAL, disclosure/dup pending** | **excluded from this repo** — live reverse-shell PoC + hostile tarball are sensitive; possible dup of Sonar 2026-04-30; verify before any submission |

## Open / not yet investigated

A05 (`--plugin-url` zip), A06 (symlink TOCTOU on deep-link cwd), A07 (IDE RPC trust), A08
(trust-inheritance via parent path), A09 (code-classifier CVE-2026-24887-style variants), A13 (OAuth
callback param injection).
