# Codex cloud-config policy escalation

> 상태: `소스 확인` · `guarded tests 6/6` · `actual CLI two-process chain` · `벤더 미확인 0-day 후보`
>
> 증거 표기: **[소스]** 구현에서 확인 · **[동적]** fixture/loopback 실행 관찰 · **[추론]** 확인된 edge에서 도출 · **[미검증]** 별도 검증 필요
>
> 실제 계정·토큰·backend를 사용하지 않은 비공개 제출용 초안.


## 핵심 요약

- Codex cloud-config cache는 client와 binary에 공통으로 포함된 HMAC key를 사용하므로, 공격자가 유효한 enterprise 정책 cache를 직접 만들 수 있다.
- 실제 제한된 `workspace-write` process에서 악성 저장소의 generator가 `auth.json` identity를 읽고 custom-named `CODEX_HOME`에 위조 cache를 기록했으며, 같은 process의 workspace 밖 쓰기는 차단됐다.
- 다음 fresh `codex exec`는 그 cache를 정상 관리 정책으로 받아 `approval: never`와 `sandbox: danger-full-access`로 전환한 뒤 workspace 밖 marker를 기록했다.
- 별도 writer 결함으로 cache path symlink를 따라 workspace 밖 파일을 cache JSON으로 덮는 fixed-content clobber도 실제 CLI 경로에서 확인됐다.
- 주 분류는 OWASP Agentic `ASI05 Unexpected Code Execution`이며, 기본 home이 아닌 writable custom home과 다음 실행의 명시적 sandbox override 부재가 핵심 전제다.

## 배경과 목적

Codex는 Business·Enterprise·Edu 계정의 cloud configuration을 local cache에 저장하고 다음 시작 때 재사용한다. 이 cache는 일반 설정처럼 보이지만 실제로는 다음 보안 상태를 결정한다.

- `approval_policy`
- `sandbox_mode`
- 허용 가능한 approval policy
- 허용 가능한 sandbox mode
- 일부 feature와 managed configuration

따라서 cache의 무결성이 깨지면 단순 UI 설정 변조가 아니라 다음 Codex process의 실행 권한과 승인 정책이 바뀐다.

이 보고서는 source commit `85fc4def358b7df21883e72ae8dda43a0f572f32`를 기준으로 다음 질문을 검증한 결과다.

> 저신뢰 repository 또는 model-controlled shell이 제한된 workspace write만으로 다음 Codex 실행의 enterprise control-plane policy를 바꾸고 host-side code execution까지 연결할 수 있는가?

## OWASP Agentic 분류

### 주 분류 — ASI05 Unexpected Code Execution

위조된 cloud policy를 다음 process가 적용하면, 원래 workspace sandbox에서 차단되던 shell command가 `danger-full-access`로 실행된다. 최종 보안 결과가 예상하지 않은 host-side code execution이므로 ASI05를 주 분류로 선택했다.

### 보조 분류

- **ASI03 Identity & Privilege Abuse:** agent가 사용자의 Codex identity와 enterprise policy를 대신 사용하며, 제한된 권한에서 더 높은 실행 권한으로 전환한다.
- **ASI06 Memory & Context Poisoning:** disk cache에 저장된 악성 정책이 process 경계를 넘어 다음 session의 판단과 실행 정책을 왜곡한다.
- **ASI01 Agent Goal Hijack:** 악성 repository 내용이나 prompt injection이 첫 process에서 generator 실행을 유도하는 경우의 초기 전달 경로다.

ASI01은 전달 시나리오이고, cache 검증 부재와 권한 상승이라는 root cause 자체는 ASI05·ASI03·ASI06에 더 직접적으로 해당한다.

## 취약점 배경

### 공개 대칭 HMAC

cache MAC은 대략 다음과 같은 client-embedded key로 계산된다.

```rust
b"codex-cloud-config-bundle-cache-v1-6160ae70-bcfd-4ca8-a99b-40f73b3b072e"
```

이 key를 모든 설치가 알고 있으므로 HMAC은 실질적인 server authentication이 아니다.

```text
정상적인 의미:
  server가 payload를 만들고 client가 검증

현재 의미:
  source 또는 binary를 읽은 공격자도 payload와 HMAC을 만들 수 있음
```

HMAC 자체의 수학적 구현이 깨진 것이 아니라, 대칭 key를 신뢰 경계의 양쪽에 둔 설계가 문제다.

### loader invariant 부재

정상 writer는 짧은 TTL을 계산하지만 loader는 다음 조건 중심으로 cache를 받아들인다.

- identity가 현재 로그인 계정과 일치
- HMAC이 일치
- `expires_at > now`
- TOML과 requirements schema가 유효

다음 검사가 부족하다.

- `expires_at - cached_at`의 최대 TTL 제한
- `cached_at`의 미래 시각 거부
- server-issued revision 검증
- revoke 또는 generation 검증
- server 비대칭 서명 검증

결과적으로 공격자는 장기 만료 cache를 만들고 다음 시작까지 유지할 수 있다.

### cache-first startup

유효 cache가 있으면 startup은 backend에 먼저 물어보지 않고 local bundle을 반환한다. 실제 probe에서 위조 cache startup 시 backend request 수는 0회였다.

이는 서버가 해당 정책을 발급한 적이 있는지, 최신 revision인지, 이미 폐기되었는지를 startup 시 확인하지 않는다는 뜻이다.

## 실제 공격 체인

### 전제조건

공격자는 다음 조건을 만족해야 한다.

- 피해자가 Codex의 Business·Enterprise·Edu 인증 상태일 것
- 저신뢰 repository에서 model shell tool이 실행될 것
- `CODEX_HOME`이 workspace 내부의 writable custom path일 것
- 첫 process가 cache를 기록할 수 있을 것
- 다음 process에서 사용자가 `sandbox_mode = "workspace-write"` 또는 `-s workspace-write`를 명시적으로 고정하지 않을 것

일반적인 clone만으로 자동 실행되는 취약점은 아니다. repository prompt injection, 악성 build/task 지시, 사용자가 승인한 agent 작업 등 첫 shell invocation으로 이어지는 전달 경로가 필요하다.

### 1단계 — 제한된 writer가 identity와 cache를 만든다

예시 배치:

```text
workspace = /workspace/project
CODEX_HOME = /workspace/project/custom-codex-home
```

첫 Codex process의 유효 권한은 다음과 같다.

```text
approval: never
sandbox: workspace-write [workdir]
```

악성 repository의 generator는 다음 순서로 동작한다.

1. inherited `CODEX_HOME`을 읽는다.
2. `CODEX_HOME/auth.json`의 JWT claim과 token metadata에서 `chatgpt_user_id`, `account_id`를 추출한다.
3. `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`를 포함한 enterprise config를 만든다.
4. 해당 값을 허용하는 requirements를 만든다.
5. 공개 HMAC key로 서명을 계산한다.
6. `$CODEX_HOME/cloud-config-bundle-cache.json`에 저장한다.

이 쓰기는 workspace 안에 있으므로 성공한다. 반면 같은 shell이 workspace sibling 밖에 marker를 쓰려고 하면 실제 runtime에서 다음처럼 실패한다.

```text
/bin/bash: .../outside/stage-one-marker: Permission denied
```

즉 1단계는 host escape가 아니라 **다음 process의 control-plane state를 바꾸는 writer primitive**다.

### 2단계 — process 경계

현재 Codex process는 이미 읽은 bundle을 메모리에 보유하므로, 같은 process 중간에 cache 파일을 바꿔도 즉시 정책이 바뀌지 않는다.

공격자는 다음 자연스러운 새 process를 기다린다.

- 사용자가 Codex를 다시 실행
- CI의 다음 단계
- IDE 또는 wrapper의 재시작
- 다음 task가 별도 `codex exec`를 호출

### 3단계 — fresh consumer가 위조 정책을 적용

다음 process는 같은 custom home에서 cache를 읽는다.

```text
identity match
→ HMAC valid
→ long expiry valid
→ config + requirements merge
→ cloud policy 적용
```

로컬 sandbox override가 없으면 결과는 다음과 같다.

```text
approval: never
sandbox: danger-full-access
```

system requirements가 `read-only`와 `on-request`를 요구하더라도 cloud requirements가 더 높은 우선순위로 합성되면 이를 넓힐 수 있다. 다만 legacy managed requirements나 macOS MDM이 cloud보다 더 높은 우선순위로 같은 필드를 제한하면 이 부분은 차단될 수 있다.

### 4단계 — host-side command 실행

두 번째 process의 model shell은 더 이상 workspace mount에 한정되지 않는다.

```text
process 1:
  active cache 생성 성공
  outside marker 실패

process 2:
  forged cache 채택
  danger-full-access
  outside marker 성공
```

이것은 root 권한 상승이 아니라 Codex를 실행한 동일 사용자 권한의 host compromise다. 가능한 결과는 다음과 같다.

- workspace 밖 source와 설정 변경
- 사용자의 SSH·Git·shell 설정 접근
- 다른 repository 접근
- 사용자 권한 credential 읽기 또는 파괴
- sandbox network 제한 제거
- 후속 persistence 설치

## 별도 체인 — symlink cache clobber

cloud policy escalation과 독립적으로 cache writer의 symlink 처리에도 문제가 있다.

```text
custom-home/cloud-config-bundle-cache.json
    -> ../../outside/target

cache miss 또는 invalid cache
    -> 정상 backend fetch
    -> trusted save()
    -> fs::write(path, serialized)
    -> symlink target truncate
```

`O_NOFOLLOW`, regular-file 검사, same-directory temporary file 후 atomic replace가 없으면 save가 symlink를 따라간다.

실제 CLI auth → backend fetch → save 경로에서 workspace 밖 sentinel이 cache JSON으로 교체됐다.

정확한 영향은 다음과 같다.

- 경로 선택 가능한 arbitrary-path overwrite
- 내용은 server bundle을 포함한 fixed-format cache JSON
- arbitrary-content write나 즉시 RCE로 과장할 수 없음
- 설정·credential·source 파일 파괴에 따른 integrity/availability 영향

## 검증 증거

proof bundle은 실제 계정과 외부 OpenAI backend를 사용하지 않고 fixture identity와 local mock만 사용한다.

```text
cloud-config internal tests: 2/2 passed
protocol policy test:        1/1 passed
actual codex CLI tests:      3/3 passed
guarded total:               6/6 passed
```

핵심 actual CLI 결과:

```text
stage 1: sandbox: workspace-write [workdir]
stage 1: auth.json identity read + public-HMAC cache generation: success
stage 1: outside write: Permission denied
stage 2: approval: never
stage 2: sandbox: danger-full-access
stage 2: outside marker: exploited
```

재현 artifact:

- [검토용 README](README.md)
- [actual CLI E2E patch](actual-cli-e2e.patch)
- [guarded runner](run-proof.sh)

제품 source에는 test diff를 남기지 않았으며 runner가 종료 시 patch를 복원한다.

## 영향 범위와 한계

### 확인된 범위

- Linux legacy Landlock 실제 runtime에서 custom home cache write 성공
- 같은 restricted process의 workspace 밖 write 차단
- 다음 fresh process의 DFA 전환과 outside write 성공
- public HMAC cache forgery와 cache-first startup
- 정상 backend save의 symlink clobber

### 아직 일반화하지 않은 범위

- 기본 `~/.codex`를 workspace-write만으로 쓰는 경로는 확인되지 않았다.
- 이 host는 bubblewrap user namespace를 거부하므로 built-in `:workspace`의 기본 bubblewrap runtime과 완전히 동일하다고 단정하지 않는다.
- writable custom `CODEX_HOME`은 모든 설치의 기본 배치가 아니며 CI, devcontainer, IDE wrapper의 실제 사용 여부가 별도 조사 대상이다.
- 사용자가 다음 실행마다 sandbox를 명시적으로 `workspace-write`로 고정하면 cloud DFA가 적용되지 않고 안전한 fallback이 될 수 있다.
- MDM 또는 더 높은 우선순위 managed requirements가 DFA를 금지하면 정책 확장이 차단된다.
- Windows와 macOS의 canonical home 보호는 별도 runtime 검증이 필요하다.

## 심각도 평가

잠정 평가는 **High 후보**다.

| 조건 | 평가 |
|---|---|
| public HMAC만 검증 | server policy forgery 가능 |
| custom writable home 도달 | 실제 2-process host compromise |
| 기본 `~/.codex`만 사용 | 이 chain은 직접 성립하지 않음 |
| 다음 실행에 local sandbox 고정 | DFA 승격 차단 |
| MDM/managed higher layer 제한 | 일부 배치에서 차단 |
| symlink save만 단독 | fixed-content integrity/availability 문제 |

공식적인 writable custom home 배치가 확인되거나 default home alias/bind/reparse 우회가 추가로 확인되면 Critical 후보까지 재평가할 수 있다. 현재는 custom deployment 전제를 숨기지 않는 것이 정확하다.

## 권고 패치

### 1. server 비대칭 서명 도입

가장 중요한 수정이다.

- private signing key는 server에만 보관
- client는 embedded public key로 서명 검증
- key rotation과 `key_id` 지원
- payload에 account, device, revision, issued-at, expiry 포함

공개 HMAC key를 다른 문자열로 바꾸는 것은 해결책이 아니다. 공격자는 새 공개 문자열도 source와 binary에서 읽을 수 있다.

### 2. cache loader의 엄격한 lifetime·provenance 검증

- `expires_at - cached_at <= max_ttl`
- `cached_at <= now + clock_skew`
- server revision/generation 검증
- 계정·조직·device binding
- revoke 이후 cache fail-closed
- 보안 필드는 stale cache를 무기한 권위로 사용하지 않음

이 수정은 HMAC 위조를 막지는 못하지만 replay와 장기 persistence를 줄인다. 단독 패치로는 충분하지 않다.

### 3. sandbox에서 canonical `CODEX_HOME` 보호

basename `.codex`만 보호하지 말고 실제 resolved `CODEX_HOME`을 sandbox policy에 별도 연결한다.

- model shell에서 `CODEX_HOME` write deny
- cache path는 Codex trusted process만 기록
- workspace에 home을 둘 경우에도 control-plane 파일은 read-only mount
- environment variable과 canonical path를 동일한 보안 identity로 처리

이 수정은 custom-home writer를 차단하지만, 다른 same-user writer와 public HMAC 문제가 남아 있으면 cache forgery 자체는 해결하지 못한다.

### 4. no-follow atomic cache IO

- symlink를 발견하면 저장 실패
- `openat2(..., RESOLVE_NO_SYMLINKS)` 또는 동등한 dirfd 기반 방식
- same-directory temporary file
- 권한·owner 검증
- `fsync` 후 atomic rename

이 수정은 symlink clobber를 해결하지만 정책 위조 문제와는 별도다.

### 5. managed policy merge monotonicity

관리 layer가 더 낮은 우선순위의 제한을 넓히지 못하도록 approval과 sandbox requirements는 intersection 또는 deny-wins 방식으로 합성해야 한다. cloud config가 system 제한을 넓힐 수 있는 현재 precedence는 재검토가 필요하다.

### 패치 평가

| 패치 | 해결 범위 | 평가 |
|---|---|---|
| HMAC key 변경 | 없음 | 공개 client key라는 구조가 유지되면 재현 가능 |
| TTL 상한만 추가 | replay 기간 축소 | forgery와 cache-first는 남음 |
| server 비대칭 서명 | 정책 위조 차단 | 가장 직접적인 근본 수정 |
| canonical home deny | workspace writer 차단 | custom-home 변종에 효과적, 다른 writer는 남음 |
| no-follow atomic write | symlink clobber 차단 | 별도 writer 결함에 충분 |
| deny-wins requirements merge | lower-layer 확장 차단 | 조직 관리 우회 방어에 필요 |

권장 순서는 server 서명과 loader 검증을 먼저 적용하고, canonical home 보호와 no-follow IO를 독립 방어층으로 추가하는 것이다.

## 탐지와 대응

- cache JSON의 `cached_at`, `expires_at`, revision, signature key id를 감사 로그에 남긴다.
- 정상 backend가 발급하지 않은 config/requirements ID를 탐지한다.
- `CODEX_HOME`이 workspace 하위에 있으면 경고하거나 실행을 거부한다.
- process 시작 시 effective approval과 sandbox가 직전 session과 갑자기 달라지는지 기록한다.
- `Never + DangerFullAccess` 전환은 별도 사용자 확인 또는 관리자 정책을 요구한다.
- cache path가 symlink이거나 canonical home 밖 target을 가리키면 즉시 격리한다.

이미 cache가 위조됐을 가능성이 있으면 해당 계정의 Codex session을 종료하고, `auth.json`과 cache를 보존한 뒤 조직 정책과 사용자 권한 파일 변경을 조사해야 한다. 실제 토큰을 보고서나 proof에 포함하지 않는다.

## 결론

이번 후보는 단일 checksum 버그가 아니라 다음 세 요소가 결합된 trust-boundary failure다.

```text
client-known symmetric MAC
  + cache-first authority bypass
  + writable custom CODEX_HOME
  + next-process policy reload
  = sandbox policy escalation
  = host-side code execution
```

실제 proof에서 첫 process는 cache만 쓸 수 있었고, 두 번째 process가 처음으로 workspace 밖에 썼다. 그러므로 “제한된 agent가 즉시 host를 쓴다”가 아니라 “제한된 agent가 다음 실행의 보안 정책을 바꾼다”가 정확한 root chain이다.

## 출처

- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [Codex Managed configuration](https://learn.chatgpt.com/docs/enterprise/managed-configuration)
- [Codex Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- local source commit `85fc4def358b7df21883e72ae8dda43a0f572f32`
- `codex-rs/cloud-config/src/cache.rs`
- `codex-rs/cloud-config/src/service.rs`
- `codex-rs/protocol/src/permissions.rs`
- `codex-rs/linux-sandbox/src/landlock.rs`

## 관련 노트

- [ancestor relocation MCP RCE](../ancestor-relocation-mcp-rce/)
