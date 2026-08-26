# Codex (OpenAI) — OWASP ASI Top 10 커버리지

OWASP Agentic Security Initiative(ASI) Top 10 분류로 본 어택 서피스 커버리지.
**판정(🟢 KILLED / 🔴 LIVE / 🟡 INFO / ⚪ PATCHED)은 개별 기법에만 붙는다.** 한 카테고리에 기법이 여럿이라, 카테고리 전체를 한 판정으로 못 묶는다 — '검증' 칸은 몇 건을 어떤 판정으로 봤는지, '미탐색'은 같은 카테고리에서 아직 안 판 변형 수다. 자세한 건 각 카테고리 README.

| ASI | 카테고리 | 검증 커버리지 | 미탐색 | 폴더 |
|---|---|---|---|---|
| ASI01 | Agent Goal Hijack | ☐ 미조사 | 다수(미조사) | [ASI01-agent-goal-hijack](ASI01-agent-goal-hijack/) |
| ASI02 | Tool Misuse & Exploitation | 🔴 기법 2건(LIVE, 제보 예정) · 미탐색 6+ | 6+ 변형 | [ASI02-tool-misuse-exploitation](ASI02-tool-misuse-exploitation/) |
| ASI03 | Identity & Privilege Abuse | ☐ 미조사 | 다수(미조사) | [ASI03-identity-privilege-abuse](ASI03-identity-privilege-abuse/) |
| ASI04 | Agentic Supply Chain Vulnerabilities | 🔴 기법 2건(1건 LIVE 미패치 후보, 1건 기지정 CVE 재현) · 미탐색 3+ | 3+ 변형 | [ASI04-agentic-supply-chain](ASI04-agentic-supply-chain/) |
| ASI05 | Unexpected Code Execution (RCE) | 🔴 기법 6건(LIVE/조건부 후보, 제보 예정) · 미탐색 2+ | 2+ 변형 | [ASI05-unexpected-code-execution](ASI05-unexpected-code-execution/) |
| ASI06 | Memory & Context Poisoning | 🔴 기법 1건(LIVE primitive/조건부 full-chain, 제보 예정) · 미탐색 3+ | 3+ 변형 | [ASI06-memory-context-poisoning](ASI06-memory-context-poisoning/) |
| ASI07 | Insecure Inter-Agent Communication | ☐ 미조사 | 다수(미조사) | [ASI07-insecure-inter-agent-comms](ASI07-insecure-inter-agent-comms/) |
| ASI08 | Cascading Failures | ☐ 미조사 | 다수(미조사) | [ASI08-cascading-failures](ASI08-cascading-failures/) |
| ASI09 | Human-Agent Trust Exploitation | ☐ 미조사 | 다수(미조사) | [ASI09-human-agent-trust-exploitation](ASI09-human-agent-trust-exploitation/) |
| ASI10 | Rogue Agents | ☐ 미조사 | 다수(미조사) | [ASI10-rogue-agents](ASI10-rogue-agents/) |
