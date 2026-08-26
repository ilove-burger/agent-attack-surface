# agent-attack-surface

AI 코딩 에이전트 화이트햇 리서치의 **커버리지 맵** — **Claude Code**(Anthropic)와
**Codex**(OpenAI) 대상. 범위: **coordinated disclosure**(HackerOne Anthropic / OpenAI Codex).
"어떤 어택 서피스를 팠고 각각의 판정이 뭔지"를 **OWASP Agentic Security Initiative(ASI) Top 10**
분류로 정리한 *색인*이라, 팀원끼리 같은 데를 중복해서 파지 않게 하는 게 목적이다. 실제 재현은
**`hunma_agent`** 하네스에 있고(marker-only, bwrap 격리, mock Anthropic API, 실제 아티팩트),
각 기법 폴더가 해당 `compare-*` 스크립트를 링크한다.

> **Private repo.** 일부 서피스는 미패치이거나 제보 진행 중인 이슈를 다룬다. 공개·재배포 금지.
> 실제 무기화(리버스셸, 악성 아티팩트)는 여기 커밋하지 않는다.

## 관련 저장소 & 컨벤션

이 repo는 **novel 어택 서피스 커버리지 맵**이다. 짝이 되는 **[hunma_agent](https://github.com/ilove-burger/hunma_agent)**
는 알려진 CVE를 root-cause·보안 불변식 중심으로 분석·재현하는 **CVE 분석 사례집 + 재현 엔진**이다.
여기 있는 재현 하네스(`compare-*`)도 hunma_agent 안에서 돈다. 두 repo는 hunma_agent의 컨벤션을 공유한다:

- **root-cause를 "X ≠ Y" 보안 불변식으로** 표기 (예: `untrusted project environment ≠ trusted configuration locator`).
  각 finding 상단의 *시험한 보안 경계* 필드가 이것.
- **정밀 분석-상태 어휘** — 단일 "됨/안됨"이 아니라 증거 수준을 구분:
  `소스 확인` · `배포 artifact 확인` · `패치 확인` · `공개 PoC 확인` · `부분 동적 검증` · `E2E 재현` ·
  `version boundary`. defended(KILL) finding은 `E2E marker 재현(공격 실패 → 불변식 유지)`로 표기.
- **OWASP ASI는 보조 분류**로 쓰고 번호만 붙이지 않는다 — 각 finding에 Primary/Secondary와 실제 agent
  behavior 연결을 적는다.

## 읽는 법 — 판정은 기법 단위, 카테고리는 커버리지

**한 ASI 카테고리엔 기법이 여러 개다.** 예: ASI04(Supply Chain)엔 MCP 결과 위조, MCP 툴 정의
오염, `.mcp.json` consent 우회, `--plugin-url` zip, 플러그인 공급망 … 이 있다. 그래서:

- 🟢 KILLED / 🔴 LIVE / 🟡 INFO / ⚪ PATCHED 같은 **판정은 개별 기법에만** 붙는다.
- **카테고리는 "판정"이 없다.** 대신 "몇 개 기법을 어떤 판정으로 검증했고, 같은 카테고리에서
  아직 안 판 변형(**미탐색 표면**)이 몇 개인지"로 커버리지를 표시한다. 검증된 기법이 있어도 그
  카테고리가 '끝난' 건 아니다.
- ↗ **external** = 팀원(malhyuk) 워크스페이스 인계, 여기서 미재검증(포인터만). ☐ **미조사**.

## 구조

```
claudecode/                 # Claude Code — ASI01..ASI10
  README.md                 # 제품 커버리지 인덱스
  ASI04-agentic-supply-chain/
    README.md               # 카테고리: 검증한 기법 + 미탐색 표면
    mcp-forged-tool-use/README.md   # 기법: 가설·불변식·방법·판정
  ...
codex/                      # Codex — ASI01..ASI10
```

## Claude Code

| ASI | 카테고리 | 검증한 기법 (판정) | 미탐색 |
|---|---|---|---|
| [ASI01](claudecode/ASI01-agent-goal-hijack/) | Agent Goal Hijack | WebFetch 웹 콘텐츠 IPI → 🟢 killed | 6+ 변형 |
| [ASI02](claudecode/ASI02-tool-misuse-exploitation/) | Tool Misuse & Exploitation | Bash LLM 분류기 인젝션 → 🟢 killed; 코드 분류기 우회 → 🟢 killed(↗) | 5+ 변형 |
| [ASI03](claudecode/ASI03-identity-privilege-abuse/) | Identity & Privilege Abuse | 딥링크 재주입 ⚪(↗), NM7 trust 우회 🟡(↗) — 여기서 미검증 | 6+ 변형 |
| [ASI04](claudecode/ASI04-agentic-supply-chain/) | Agentic Supply Chain | 악성 MCP tool_use 위조 → 🟢 killed | 6+ 변형 |
| [ASI05](claudecode/ASI05-unexpected-code-execution/) | Unexpected Code Execution (RCE) | git fsmonitor pre-trust RCE → 🔴?(↗, 본문 제외) | 6+ 변형 |
| [ASI06](claudecode/ASI06-memory-context-poisoning/) | Memory & Context Poisoning | 악성 CLAUDE.md IPI → 🟢 killed | 6+ 변형 |
| [ASI07](claudecode/ASI07-insecure-inter-agent-comms/) | Insecure Inter-Agent Communication | — | ☐ 미조사 |
| [ASI08](claudecode/ASI08-cascading-failures/) | Cascading Failures | — | ☐ 미조사 |
| [ASI09](claudecode/ASI09-human-agent-trust-exploitation/) | Human-Agent Trust Exploitation | — | ☐ 미조사 |
| [ASI10](claudecode/ASI10-rogue-agents/) | Rogue Agents | — | ☐ 미조사 |

**검증된 4개 기법(ASI01/02/04/06)의 공통 구조:** load-bearing 통제는 *구조적* 코드 계층 불변식이다 —
MCP 결과의 콘텐츠 타입 화이트리스트, provenance(`tool_use`는 오직 assistant 턴에서만 인정),
rule-match/AST permission. 속일 수 있는 LLM/데이터/컨텍스트/웹 계층은 non-load-bearing: 인젝션이
최대로 성공해도 permission layer가 유도된 명령을 독립적으로 거부하므로 얻는 권한이 0이다. **단,
이건 검증한 그 기법들에 한한 결론이고, 각 카테고리의 미탐색 표면은 열려 있다.**

## Codex

| ASI | 카테고리 | 검증한 기법 (판정) | 미탐색 |
|---|---|---|---|
| [ASI02](codex/ASI02-tool-misuse-exploitation/) | Tool Misuse & Exploitation | project-local ripgrep config → approval 없는 `--pre` 실행 및 workspace 밖 canary 읽기 → 🔴 LIVE (제보 예정); `bash -lc` 반복 `!` negation → dangerous-command classifier + admin 정책 + `Never` hard-stop 동시 우회 → 🔴 LIVE (제보, 트리아지 대기중); PowerShell hashtable splat 변형 → 🟡 INFO (duplicate로 CLOSED) | 4+ 변형 |
| [ASI04](codex/ASI04-agentic-supply-chain/) | Agentic Supply Chain | CVE-2025-61260 `.env`→`CODEX_HOME` 재지정→로컬 MCP spawn → 🟢 재현 | 4+ 변형 |
| [ASI05](codex/ASI05-unexpected-code-execution/) | Unexpected Code Execution (RCE) | 승인된 project hook 대상 스크립트 치환 → sandbox-외부 same-user RCE → 🔴 LIVE (제보 예정) | 4+ 변형 |
| ASI01·03·06·07·08·09·10 | (나머지 카테고리) | — | ☐ 미조사 |

## 재현 방법

모든 🟢는 **`hunma_agent`** 하네스의 결정론적 실행이다. 이 repo 옆에 클론:

```
git clone <hunma_agent remote>
cd hunma_agent && ./harness/compare-claude-webfetch-ipi --repeat 2   # (또는 compare-claude-bash-classifier-injection / -mcp-forged-tooluse / -claudemd-ipi / compare-codex-61260)
```

하네스는 SHA-256 고정 아티팩트(`harness/versions/manifest.json`)를 쓰고, 실제 CLI를 bwrap 아래에서
loopback mock Anthropic API를 상대로 돌린 뒤 marker-only 오라클로 판정한다(`touch marker`는 공격이
실제로 실행 권한을 얻었을 때만 생성). 각 기법 폴더의 **Files** 절에 정확한 fixtures·cases가 있다.
