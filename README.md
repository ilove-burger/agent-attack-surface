# agent-attack-surface

AI 코딩 에이전트 화이트햇 리서치의 **커버리지 맵** — **Claude Code**(Anthropic)와
**Codex**(OpenAI) 대상. 범위: **coordinated disclosure**(HackerOne Anthropic / OpenAI Codex).
이 repo는 "어떤 어택 서피스를 팠고 각각의 판정이 뭔지"를 **OWASP Agentic Security Initiative(ASI)
Top 10** 분류로 정리한 *색인*이라, 팀원끼리 같은 데를 중복해서 파지 않도록 하는 게 목적이다.
실제로 돌아가는 재현은 **`hunma_agent`** 하네스에 있고(marker-only, bwrap 격리, mock Anthropic API,
실제 Claude Code / Codex 아티팩트), 각 폴더가 해당 `compare-*` 스크립트를 링크한다.

> **Private repo.** 일부 서피스는 미패치이거나 제보 진행 중인 이슈를 다룬다. 공개·재배포 금지.
> 실제 무기화(리버스셸, 악성 아티팩트)는 여기 커밋하지 않는다.

## 구조

```
claudecode/            # Claude Code — ASI01..ASI10 카테고리
  ASI01-agent-goal-hijack/…/README.md
  ...
codex/                 # Codex — ASI01..ASI10 카테고리
```

각 제품 폴더에 ASI01~ASI10 카테고리 디렉터리가 있고, 조사한 서피스는 해당 카테고리 아래에
`<서피스>/README.md`(가설·불변식·방법·판정) 로 들어간다. 조사 안 한 카테고리도 폴더+README를 두어
"어디가 비어있는지"를 보여준다.

## 범례

- 🟢 **KILLED** — 파봤고 방어됨; 공격이 권한을 못 얻음. 제보 대상 아님. (전체 writeup + 재현 하네스 포함.)
- 🔴 **LIVE** — 익스플로잇 확인됨; 제보 진행 중.
- 🟡 **INFO** — 동작하지만 "의도된/문서화된" 동작일 가능성; 낮은 심각도.
- ⚪ **PATCHED** — 옛 버전에서 live였으나 업스트림에서 수정됨.
- ↗ **external** — 팀원 워크스페이스에서 인계; **여기서 독립 재검증 안 함**(포인터만).
- ☐ **OPEN** — 아직 미조사.

## Claude Code — ASI Top 10

| ASI | 카테고리 | 상태 | 조사한 서피스 |
|---|---|---|---|
| [ASI01](claudecode/ASI01-agent-goal-hijack/) | Agent Goal Hijack | 🟢 KILLED | A02/P4 WebFetch 콘텐츠 → IPI → Bash |
| [ASI02](claudecode/ASI02-tool-misuse-exploitation/) | Tool Misuse & Exploitation | 🟢 KILLED | A14 Bash LLM 분류기 인젝션 (+ A10 ↗) |
| [ASI03](claudecode/ASI03-identity-privilege-abuse/) | Identity & Privilege Abuse | ⚪/🟡 ↗ | A01 딥링크 재주입(patched), A04 NM7 trust 우회(info) — external |
| [ASI04](claudecode/ASI04-agentic-supply-chain/) | Agentic Supply Chain | 🟢 KILLED | A03/P2 악성 MCP 서버 tool_use 위조 |
| [ASI05](claudecode/ASI05-unexpected-code-execution/) | Unexpected Code Execution (RCE) | 🔴 ↗ | A12 git fsmonitor pre-trust RCE — external, 본문 제외(민감) |
| [ASI06](claudecode/ASI06-memory-context-poisoning/) | Memory & Context Poisoning | 🟢 KILLED | A11/P3 악성 CLAUDE.md → IPI → Bash |
| [ASI07](claudecode/ASI07-insecure-inter-agent-comms/) | Insecure Inter-Agent Communication | ☐ OPEN | — |
| [ASI08](claudecode/ASI08-cascading-failures/) | Cascading Failures | ☐ OPEN | — |
| [ASI09](claudecode/ASI09-human-agent-trust-exploitation/) | Human-Agent Trust Exploitation | ☐ OPEN | — |
| [ASI10](claudecode/ASI10-rogue-agents/) | Rogue Agents | ☐ OPEN | — |

**KILL 4종(ASI01/ASI02/ASI04/ASI06)의 공통 구조:** load-bearing한 통제는 *구조적* 코드 계층
불변식이다 — MCP 결과의 콘텐츠 타입 화이트리스트, provenance(`tool_use`는 오직 assistant 턴에서만
인정), rule-match/AST permission. 속일 수 있는 LLM / 데이터 / 컨텍스트 / 웹 계층은
**non-load-bearing**: 인젝션이 최대로 성공해도 permission layer가 유도된 명령을 독립적으로 거부하므로
얻는 권한이 0이다.

## Codex — ASI Top 10

| ASI | 카테고리 | 상태 | 조사한 서피스 |
|---|---|---|---|
| [ASI01](codex/ASI01-agent-goal-hijack/) | Agent Goal Hijack | ☐ OPEN | — |
| [ASI02](codex/ASI02-tool-misuse-exploitation/) | Tool Misuse & Exploitation | ☐ OPEN | — |
| [ASI03](codex/ASI03-identity-privilege-abuse/) | Identity & Privilege Abuse | ☐ OPEN | — |
| [ASI04](codex/ASI04-agentic-supply-chain/) | Agentic Supply Chain | 🟢 재현 | CVE-2025-61260 `.env` → `CODEX_HOME` 재지정 → 로컬 MCP spawn |
| [ASI05](codex/ASI05-unexpected-code-execution/) | Unexpected Code Execution (RCE) | ☐ OPEN | — |
| [ASI06](codex/ASI06-memory-context-poisoning/) | Memory & Context Poisoning | ☐ OPEN | — |
| [ASI07](codex/ASI07-insecure-inter-agent-comms/) | Insecure Inter-Agent Communication | ☐ OPEN | — |
| [ASI08](codex/ASI08-cascading-failures/) | Cascading Failures | ☐ OPEN | — |
| [ASI09](codex/ASI09-human-agent-trust-exploitation/) | Human-Agent Trust Exploitation | ☐ OPEN | — |
| [ASI10](codex/ASI10-rogue-agents/) | Rogue Agents | ☐ OPEN | — |

## 재현 방법

여기 있는 모든 🟢는 **`hunma_agent`** 하네스에서 돌리는 결정론적 실행이다. 이 repo 옆에 클론:

```
git clone <hunma_agent remote>
cd hunma_agent && ./harness/compare-claude-p4 --repeat 2   # (또는 -a14 / -p2 / -p3 / compare-codex-61260)
```

하네스는 SHA-256으로 고정된 아티팩트(`harness/versions/manifest.json`)를 쓰고, 실제 CLI를 bwrap
아래에서 loopback mock Anthropic API를 상대로 돌린 뒤, marker-only 오라클을 판정한다(`touch marker`는
공격이 실제로 실행 권한을 얻었을 때만 생성됨). 각 서피스 폴더의 **Files** 절에 정확한 fixtures·cases가
적혀 있다.
