# Claude Code (Anthropic) — OWASP ASI Top 10 커버리지

OWASP Agentic Security Initiative(ASI) Top 10 분류로 정리한 어택 서피스 커버리지.
상태 범례는 [루트 README](../README.md). 🟢 KILLED = 파봤고 방어됨(전체 writeup+하네스), 🔴 LIVE, 🟡 INFO, ⚪ PATCHED, ↗ external(미재검증), ☐ OPEN(미조사).

| ASI | 카테고리 | 상태 | 폴더 |
|---|---|---|---|
| ASI01 | Agent Goal Hijack | 🟢 KILLED | [ASI01-agent-goal-hijack](ASI01-agent-goal-hijack/) |
| ASI02 | Tool Misuse & Exploitation | 🟢 KILLED 외 | [ASI02-tool-misuse-exploitation](ASI02-tool-misuse-exploitation/) |
| ASI03 | Identity & Privilege Abuse | 🟡 INFO 외 | [ASI03-identity-privilege-abuse](ASI03-identity-privilege-abuse/) |
| ASI04 | Agentic Supply Chain Vulnerabilities | 🟢 KILLED | [ASI04-agentic-supply-chain](ASI04-agentic-supply-chain/) |
| ASI05 | Unexpected Code Execution (RCE) | 🔴 LIVE? | [ASI05-unexpected-code-execution](ASI05-unexpected-code-execution/) |
| ASI06 | Memory & Context Poisoning | 🟢 KILLED | [ASI06-memory-context-poisoning](ASI06-memory-context-poisoning/) |
| ASI07 | Insecure Inter-Agent Communication | ☐ OPEN | [ASI07-insecure-inter-agent-comms](ASI07-insecure-inter-agent-comms/) |
| ASI08 | Cascading Failures | ☐ OPEN | [ASI08-cascading-failures](ASI08-cascading-failures/) |
| ASI09 | Human-Agent Trust Exploitation | ☐ OPEN | [ASI09-human-agent-trust-exploitation](ASI09-human-agent-trust-exploitation/) |
| ASI10 | Rogue Agents | ☐ OPEN | [ASI10-rogue-agents](ASI10-rogue-agents/) |
