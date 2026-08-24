# Codex project config 외부 파일 로딩 후속 후보 3건

## 문서 목적

이 문서는 Codex의 project-local `.codex/config.toml`이 프로젝트 밖 파일을 참조하는 경로를 조사하면서
확인한 세 후보를 팀 공유용으로 정리한다. 세 후보는 공개된 1-day를 그대로 재현한 것이 아니라,
`model_instructions_file` outside-read finding의 인접 path-like 설정을 로컬에서 독립 조사해 얻은 결과다.

세 건의 최종 집계는 다음과 같다.

| 후보 | 기술 동작 | 보안 판정 | 공유 처리 |
|---|---|---|---|
| `experimental_compact_prompt_file` outside-read | 외부 UTF-8 텍스트를 읽어 local compaction user prompt로 전달 | **KEEP — 보안 관련 variant CONFIRMED**, 독립 0-day는 UNVERIFIED | 기존 ASI04 finding의 affected sink 또는 별도 ASI04 variant로 공유 |
| `agents.<role>.config_file` outside-read | 외부의 유효한 role TOML에서 허용 필드를 읽어 child developer message에 반영 | **KILL — 동작 CONFIRMED, 독립 취약점 NOT ESTABLISHED** | ASI04 KILL ledger에 보존, 제보 대상 아님 |
| 로컬 containment patch TOCTOU | 경로 검사와 실제 open 사이 symlink 교체로 자체 제안 patch 우회 | **KILL as product finding — 로컬 patch 결함** | 기존 ASI04 finding의 hardening/patch design 절에 통합 |

여기서 “성공 1개”는 새로운 RCE/LPE를 뜻하지 않는다. 프로젝트 밖 파일을 읽어 모델 요청으로 보내는
별도 sink가 실제로 성립한다는 뜻이다. “탈락 2개”도 동적 실험이 실패했다는 의미가 아니다. 두 건 모두
기술 동작은 관찰됐지만, 하나는 정상 기능 계약과 겹치고 다른 하나는 공식 제품 코드가 아닌 자체 수정안의
결함이어서 독립 제품 취약점으로 승격하지 않은 것이다.

## 공통 대상과 검증 원칙

- 최신 대상: `codex-cli 0.149.1` Linux x64
- 최신 binary SHA-256:
  `73dc5888888f411c1f0fa7b81d866e721dcc86b527ce8e3b2cf4708661e823ba`
- 이전 로컬 containment patch binary SHA-256:
  `da4f735b005546dab4f97b21c4a6742c86227863fec1c665c58f945fc808a1b9`
- 보강한 load-once patch binary SHA-256:
  `9de4101cc757ed65c723adcde830f0cf753f94cc2f5c471bf23c76b2432d4922`
- 실제 비밀 파일 대신 case별 고유 marker만 사용했다.
- target은 user+network namespace 또는 `bwrap --unshare-net` 안에서 실행했다.
- 외부 route는 비워 두고, 필요한 Responses capture는 `127.0.0.1` loopback mock만 사용했다.
- 파일 open/read와 캡처된 request의 exact marker를 서로 다른 oracle로 판정했다.
- `OBSERVED/DELIVERED`, `NOT_OBSERVED/NOT_DELIVERED`, `UNVERIFIED`를 구분했다.

전체 무결성 확인 명령과 결과:

```bash
cd /home/guts/26y/Huntingmaster/main_Project/CVE_1day_analyze/model-instructions-3way
sha256sum -c FINAL_SHA256SUMS_2026-08-24
```

2026-08-24 재확인 결과, manifest에 포함된 harness, 세 target binary, 보고서와 최종 summary가 모두
`OK`였다.

---

## 1. KEEP — `experimental_compact_prompt_file` outside-read

### 무엇인가

신뢰된 프로젝트의 `.codex/config.toml`은 다음처럼 local compaction prompt 파일을 지정할 수 있다.

```toml
experimental_compact_prompt_file = "/project-outside/compact.txt"
```

Codex `0.149.1`은 이 경로가 project root 안에 있는지 확인하지 않고 파일을 읽는다. 읽힌 값은 단순히
메모리에 머무르지 않고 local compaction이 발생할 때 합성된 **user prompt**로 Responses 요청에 들어간다.

### source → sink

```text
trusted project .codex/config.toml
  → experimental_compact_prompt_file: AbsolutePathBuf
  → Config::try_read_non_empty_file(...)
  → Config.compact_prompt
  → local compaction request의 user message
  → 사용자가 이미 선택한 model provider
```

확인한 소스 위치:

- `codex-rs/core/src/config/mod.rs`: `experimental_compact_prompt_file`을
  `try_read_non_empty_file`로 읽어 `compact_prompt`에 저장
- `codex-rs/core/src/compact.rs`: local compaction에서 `compact_prompt` 소비

같은 함수에서 `model_instructions_file`과 `experimental_compact_prompt_file`을 각각 읽지만, 기존
`model_instructions_file` 전용 로컬 수정안은 compact prompt 경로에는 적용되지 않았다.

### 성립 조건

1. 공격자가 repository의 `.codex/config.toml`을 통제한다.
2. 사용자가 해당 project를 trusted로 승인한다.
3. project 밖에 공격자가 경로를 추측할 수 있는 readable UTF-8 파일이 존재한다.
4. local compaction 경로가 사용된다.
5. compaction이 발생한다. project config의 context/auto-compact limit로 trigger를 낮출 수 있다.

project config는 model provider endpoint를 직접 바꾸지 못한다. 따라서 공격자가 지정한 임의 endpoint로
곧바로 전송되는 것이 아니라, 사용자가 이미 선택한 provider로 전달된다. 또한 현재 기본 OpenAI provider의
일반 경로는 server-side compaction을 사용하므로 범용 기본 설치 영향은 제한된다.

### 동적 검증

최종 4-way matrix:

| case | filesystem oracle | request sink | 결과 |
|---|---|---|---|
| trusted + outside direct path | `OBSERVED` | `DELIVERED` | PASS |
| trusted + project 내부 control | `OBSERVED` | `DELIVERED` | PASS |
| untrusted + outside direct path | `NOT_OBSERVED` | `NOT_DELIVERED` | PASS |
| trusted + in-project symlink→outside | `OBSERVED` | `DELIVERED` | PASS |

이 matrix가 중요한 이유는 다음과 같다.

- outside marker의 path open과 value read를 확인해 설정 문자열만 본 것을 양성으로 오판하지 않았다.
- compaction이 실제로 일어난 뒤 request JSON 안의 user message에서 exact marker를 확인했다.
- untrusted control에서는 같은 compaction을 강제해도 파일 read와 sink가 모두 없었다. 따라서 결과는
  project trust를 통과한 project config layer에 귀속된다.
- project 내부 control은 기능 자체가 로드되지 않은 vacuous pass 가능성을 제거한다.

실제 실행 명령:

```bash
cd /home/guts/26y/Huntingmaster/main_Project/CVE_1day_analyze/model-instructions-3way
./run-compact-security-matrix.sh
```

핵심 산출물:

- 최종 matrix:
  `compact-security-matrix-runs/20260824T094028Z-667585/summary.tsv`
- 전체 case 증거:
  `compact-security-matrix-runs/20260824T094028Z-667585/`
- 최초 sink closure:
  `compact-sink-runs/20260824T071604Z-269014/requests/request-002.json`
- 상세 검증 보고:
  `../hunma_agent/codex/COMPACT-VARIANT-VERIFICATION_2026-08-24.md`

### 영향과 한계

- **확인된 primitive:** project 밖의 readable UTF-8 텍스트를 읽어 local compaction user prompt로 전달
- **기밀성:** 조건부로 성립. provider와 local-compaction 조건이 필요하다.
- **무결성:** 외부 텍스트가 모델 동작에 영향을 줄 수 있으나, trusted project가 이미 instructions를
  제공할 수 있어 incremental impact는 낮다.
- **RCE/LPE/sandbox escape:** 확인하지 않았고 현재 primitive에서 직접 나오지 않는다.
- **중복 상태:** 공개 exact duplicate는 찾지 못했지만 비공개 vendor 접수 여부는 알 수 없다.

### 판정

**KEEP — 보안 관련 variant CONFIRMED, 독립 0-day UNVERIFIED.**

기존 `model_instructions_file`과 root cause 및 수정 불변식이 같으므로 “새 RCE”로 분리하면 과장이다.
가장 정확한 표현은 **같은 project-origin path containment 결함의 추가 sink이자 patch scope gap**이다.

---

## 2. KILL — `agents.<role>.config_file` outside-read

### 무엇인가

신뢰된 project config에서 custom agent role 파일을 외부 절대경로로 지정할 수 있다.

```toml
[agents.researcher]
description = "marker-only role"
config_file = "/project-outside/researcher.toml"
```

외부 파일이 다음처럼 유효한 role TOML이면:

```toml
developer_instructions = "HUNMA_AGENT_ROLE_MARKER"
```

해당 role이 spawn될 때 marker가 child Responses 요청의 developer message로 전달됐다.

### source → sink

```text
trusted project .codex/config.toml
  → agents.<role>.config_file
  → relative/absolute path resolution
  → role TOML parse(deny_unknown_fields + ConfigToml)
  → 허용된 role override field만 projection
  → 해당 custom role spawn
  → child developer message
```

확인한 소스 위치:

- `codex-rs/core/src/config/agent_roles.rs`: `read_declared_role`,
  `read_resolved_agent_role_file`, `RawAgentRoleFileToml`
- `codex-rs/core/src/config/mod.rs`: child config에 허용된 override 반영

### 동적 검증

최신 binary와 기존 로컬 patch binary에 대해 outside/inside를 비교했다.

| target | role file | 결과 |
|---|---|---|
| latest `0.149.1` | outside | DELIVERED / PASS |
| latest `0.149.1` | inside | DELIVERED / PASS |
| old proposed-patched `0.148.0` | outside | DELIVERED / PASS |
| old proposed-patched `0.148.0` | inside | DELIVERED / PASS |

실제 실행 명령:

```bash
cd /home/guts/26y/Huntingmaster/main_Project/CVE_1day_analyze/model-instructions-3way
./run-agent-role-matrix.sh
```

핵심 산출물:

- matrix:
  `agent-role-matrix-runs/20260824T071725Z-272827/summary.tsv`
- 전체 request와 network evidence:
  `agent-role-matrix-runs/20260824T071725Z-272827/`
- 최초 exact sink:
  `agent-role-runs/20260824T062902Z-255393/requests/request-003.json`

### 왜 취약점 후보에서 탈락했나

기술 동작은 분명히 재현됐다. 그러나 보안 primitive가 좁고 정상 기능 계약과 겹친다.

1. 임의 파일의 raw bytes가 전달되는 것이 아니다. 대상은 파싱 가능한 Codex role TOML이어야 한다.
2. 알 수 없는 필드는 거부되고, 허용된 model/reasoning/personality/developer-instructions 등 bounded field만
   적용된다.
3. 파일을 지정하는 것만으로 자동 sink가 일어나지 않고 해당 role의 spawn이 필요하다.
4. child가 parent보다 강한 sandbox/approval/tool authority를 얻는 것을 관찰하지 못했다.
5. personal/project role file과 path 기반 role config는 공식 기능 설명과 자연스럽게 겹친다.
6. 일반적으로 존재하는 secret 파일이 우연히 valid role TOML이면서 허용 필드에 비밀을 담고 있을
   현실적 시나리오를 입증하지 못했다.

따라서 outside path를 수용한다는 사실만으로 project containment가 반드시 필요한 보안 계약이라고
단정하기 어렵다.

### 판정과 재개 조건

**KILL — source-to-sink CONFIRMED, 독립 보안 취약점 NOT ESTABLISHED.**

다음 중 하나가 새로 입증될 때만 재개한다.

- 일반적인 외부 민감 파일이 별도 가공 없이 valid role TOML로 수용되고 민감값이 전달됨
- 외부 role config가 parent보다 강한 sandbox/approval/tool authority를 부여함
- trust 전 또는 role spawn 전 자동 read/sink가 발생함

현재 상태에서는 취약점 제보 대상이 아니라 provenance 경고나 project-local role file 권장 같은
hardening 메모가 적절하다.

---

## 3. KILL — 로컬 `model_instructions_file` containment patch TOCTOU

### 무엇인가

기존 finding에 대해 자체 작성한 첫 수정안은 project-origin `model_instructions_file`의 경로를
`canonicalize()`하여 project 안인지 검사했다. 그러나 검사와 실제 파일 읽기가 같은 열린 객체에
결합되지 않았다.

```text
canonicalize(path) → project 내부 symlink target 확인
                      [공격자가 symlink 교체]
open(path)         → project 밖 파일 open/read
```

canonicalize 실패도 허용하는 fail-open 분기가 있어 symlink를 빠르게 제거·재생성하면 검사와 사용 사이의
filesystem identity가 바뀔 수 있었다.

### 동적 검증

내부 benign 파일과 외부 marker 파일 사이에서 symlink를 반복 교체하며 marker-only로 검사했다.

- syscall oracle: 24회 중 6회 `OUTSIDE_OBSERVED`
- Responses sink oracle: 20회 중 1회 `OUTSIDE_DELIVERED`
- exact sink 성공: attempt 8

실제 실행 명령:

```bash
cd /home/guts/26y/Huntingmaster/main_Project/CVE_1day_analyze/model-instructions-3way
./run-patch-toctou-probe.sh
./run-patch-toctou-sink.sh
```

핵심 산출물:

- syscall 결과:
  `toctou-runs/20260824T053028Z-226050/summary.tsv`
- sink 결과:
  `toctou-sink-runs/20260824T053310Z-240573/summary.tsv`
- exact sink:
  `toctou-sink-runs/20260824T053310Z-240573/attempt-8/request.json`

### 왜 제품 취약점 후보에서 탈락했나

우회 자체는 실제다. 하지만 공격 대상은 OpenAI가 배포한 공식 patch가 아니라 이 연구 카드에 포함한
**로컬 제안 patch**다. 따라서 이를 Codex의 별도 0-day나 vendor patch bypass라고 보고하면 provenance가
틀린다. 이 결과가 증명하는 것은 제품의 새로운 결함이 아니라 첫 수정 설계가 불완전했다는 사실이다.

### 보강과 음성 대조

수정안을 다음처럼 바꿨다.

- canonicalization 실패 시 fail closed
- project layer를 로드할 때 안전한 경로에서 파일을 한 번만 읽음
- 읽은 immutable instructions 값을 이후 단계로 전달하여 pathname을 다시 열지 않음

보강 binary에 동일 race를 다시 적용한 결과:

| 실험 | 결과 |
|---|---|
| syscall race 24회 | 0/24 outside read, `NOT_REPRODUCED` |
| sink race 20회 | 0/20 delivery, `NOT_REPRODUCED` |
| 정상 3-way control | outside 차단, inside 전달, 6/6 PASS |
| targeted regression | 4/4 PASS |
| `codex-config` 전체 | 263/263 PASS |

재검증 명령:

```bash
cd /home/guts/26y/Huntingmaster/main_Project/CVE_1day_analyze/model-instructions-3way
TOCTOU_TARGET="$PWD/artifacts/targets/codex-0.148.0-load-once-debug" \
  ./run-patch-toctou-probe.sh
TOCTOU_TARGET="$PWD/artifacts/targets/codex-0.148.0-load-once-debug" \
  ./run-patch-toctou-sink.sh
```

보강 후 산출물:

- syscall: `toctou-runs/20260824T073915Z-340887/summary.tsv`
- sink: `toctou-sink-runs/20260824T074423Z-438823/summary.tsv`
- normal control: `sink-runs/20260824T074641Z-451978/`

### 판정

**KILL as independent product finding — local patch hardening result.**

팀에는 버리지 말고 기존 finding의 patch design 교훈으로 공유해야 한다. 더 강한 최종 설계는 문자열 경로의
재검사보다 open handle을 먼저 확보하고, 검사한 filesystem object와 읽는 object가 동일함을 보장하는
방식이다.

---

## 세 후보의 공통 보안 불변식

```text
project가 설정한 경로의 문자열
    ≠
사용자가 project trust로 읽기를 승인한 filesystem object와 provenance
```

path-like config를 평가할 때는 다음을 별도로 확인해야 한다.

1. 어느 config layer가 경로를 공급했는가?
2. project-origin 값이면 project root containment가 필요한가?
3. lexical path, canonical path, 열린 object 중 무엇을 승인·검사했는가?
4. 검사와 사용 사이에 symlink/rename으로 identity가 바뀔 수 있는가?
5. 읽은 값이 실제 model request, command execution 또는 외부 sink에 도달하는가?
6. project trust 전에도 side effect가 발생하는가?
7. 문서화된 external/shared-file 기능과 충돌하지 않는가?

이 기준으로 보면 compact prompt는 실제 outside read와 request sink가 모두 성립해 남고, agent role은
기능 계약·형식·spawn 제약 때문에 죽으며, TOCTOU는 제품 finding이 아니라 수정 설계 품질 검증으로
귀속된다.

## 공유 GitHub 배치 판단

사용자가 제시한 경로:

```text
codex/ASI05-unexpected-code-execution/hook-target-script-substitution/
```

이 위치에는 올리지 않는 것이 맞다. hook finding은 승인된 command identity와 실제 대상 스크립트
contents가 분리되어 **command sandbox 밖 same-user RCE**로 이어지는 ASI05 finding이다. 이 문서의 세
후보는 project-origin file path와 model-context/config loading provenance 문제이며, RCE primitive를
공유하지 않는다.

공유 저장소 관례에 맞는 권장 배치는 다음과 같다.

### 권장안

```text
codex/ASI04-agentic-supply-chain/
├── README.md
├── project-model-instructions-outside-read/
│   ├── README.md
│   ├── DISCLOSURE.md
│   ├── HARDENING.md
│   └── ...
├── project-compact-prompt-outside-read/
│   └── README.md
└── agent-role-config-outside-read/
    └── README.md
```

- **compact prompt:** `project-compact-prompt-outside-read/README.md`를 새로 만들되, 상단에서
  `project-model-instructions-outside-read`의 variant/scope-gap임을 명시한다. ASI04 상위 README 표에는
  독립 LIVE 0-day가 아니라 `🔴 CONFIRMED VARIANT`처럼 구분해 추가한다.
- **agent role:** 중복 탐색을 막는 것이 저장소 목적이므로 KILL 문서도 남길 가치가 있다.
  `agent-role-config-outside-read/README.md`에 `KILLED / 제보 대상 아님`으로 기록하고 ASI04 인덱스에도
  KILL 한 줄을 추가한다.
- **TOCTOU:** 별도 finding 폴더를 만들지 않는다. 기존
  `project-model-instructions-outside-read/HARDENING.md`의 “rejected patch design / TOCTOU” 절로 넣고,
  필요하면 `proposed-fix.patch`를 load-once 또는 open-handle 설계로 교체한다. 공식 vendor patch처럼
  표현하지 않는다.

### 한 폴더로만 공유해야 한다면

세 건을 하나의 문서로만 올려야 할 경우 차선 위치는 다음이다.

```text
codex/ASI04-agentic-supply-chain/project-model-instructions-outside-read/FOLLOWUP_VARIANTS.md
```

그러나 장기적으로는 KEEP/KILL의 인덱싱이 흐려지므로 위 권장안처럼 compact와 agent-role을 기법별로
분리하고 TOCTOU만 기존 hardening에 합치는 편이 낫다.

## 원본 연구 파일

- 종합 판단:
  `CVE_1day_analyze/hunma_agent/codex/CANDIDATE-2WAY-ASSESSMENT_2026-08-24.md`
- compact 카드:
  `CVE_1day_analyze/hunma_agent/codex/CANDIDATE-project-compact-prompt-outside-read.md`
- agent role 카드:
  `CVE_1day_analyze/hunma_agent/codex/CANDIDATE-agent-role-config-outside-read.md`
- TOCTOU 카드:
  `CVE_1day_analyze/hunma_agent/codex/CANDIDATE-model-instructions-patch-toctou.md`
- 전체 실행 보고:
  `CVE_1day_analyze/hunma_agent/codex/DAILY_HUNT_REPORT_2026-08-24.md`
- harness와 모든 evidence:
  `CVE_1day_analyze/model-instructions-3way/`

## 최종 공유 문구

> `experimental_compact_prompt_file`은 trusted project가 project 밖 readable UTF-8 텍스트를 읽어
> local-compaction user prompt로 전달하는 source-to-sink가 Codex CLI 0.149.1에서 확인됐다. 이는
> `model_instructions_file` outside-read와 같은 project-origin path containment root cause의 별도 sink이며,
> 독립 RCE가 아니다. `agents.<role>.config_file` outside-read는 valid role TOML·bounded projection·role
> spawn 제약과 공식 기능 계약 때문에 독립 취약점으로 폐기했다. 자체 containment patch의 TOCTOU는
> 실제 재현됐지만 vendor 제품 finding이 아니라 patch-design 결함이며 load-once 보강 뒤 동일 race가
> syscall 0/24, sink 0/20으로 닫혔다.
