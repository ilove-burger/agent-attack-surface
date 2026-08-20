# OpenAI Codex CLI — 승인된 project hook의 대상 스크립트 치환을 통한 sandbox-외부 코드 실행

> 상태: `소스 확인` · `unit test 재현(rust-v0.148.0)` · `E2E sink 재현` · `실제 UI/API 승인 E2E 재현(bypass 없이, 0.148.0 바이너리)` · `벤더 미확인 0-day 후보`
>
> 증거 표기: **[소스]** source에서 확인 · **[동적]** 로컬 실험 관찰 · **[추론]** 근거에서 도출

## [1] 개요

| 항목 | 내용 |
|---|---|
| 제품 | OpenAI Codex CLI (`@openai/codex`) |
| 확인 버전 | `codex-cli 0.148.0` (npm `@openai/codex@0.148.0-linux-x64`, latest dist-tag) |
| 소스 기준 | `rust-v0.148.0` (blobless clone). 0.147→0.148 diff는 cosmetic — 해시 로직 불변 |
| 플랫폼 | Linux (unix 경로). macOS/Windows는 별도 검증 필요 |
| 심각도(제안) | High — 승인 경계를 넘어 command sandbox 밖에서 same-user 코드 실행 |
| CWE(잠정) | CWE-345 (Insufficient Verification of Data Authenticity), 관련 CWE-353 (Missing Support for Integrity Check) |
| OWASP Agentic | Primary ASI05 (Unexpected Code Execution / RCE) · Secondary ASI02 (Tool Misuse & Exploitation) |
| 최종 확인일 | 2026-08-21 |

**한 줄 요약:** **[소스]** Codex는 project hook의 신뢰 상태를 hook **정의**(event/matcher/command
문자열)의 해시로만 판정하고 command가 참조하는 **스크립트 파일의 내용**은 해시에 포함하지 않는다.
따라서 한 번 승인된 hook의 스크립트 내용을 out-of-band로 교체하면, 신뢰 해시가 불변이라 재승인 없이
`Trusted`로 남고, 이벤트 발생 시 교체된 스크립트가 **command sandbox 밖에서 사용자 권한으로** 실행된다.

## [2] 깨진 보안 경계 (불변식)

```
승인된 hook의 trust 해시가 커버하는 대상  ≠  실제로 실행되는 스크립트 파일의 내용
```

Codex는 승인 이후 변경 감지를 **명시적으로 약속**한다: 신뢰 해시가 바뀌면 hook 상태를 `Modified`로
표시하고 재승인을 요구한다. 그러나 보안상 가장 중요한 **실제 실행 내용의 변경**은 이 감지에서 누락된다.

## [3] Attack Vector

- **공격자 통제 입력:** 프로젝트 저장소의 hook 스크립트 파일 내용 (예: `<project>/.codex/hooks/check.sh`).
- **전달 경로:** 피해자가 저장소를 clone/`git pull` 하거나, 저장소 업데이트·서브모듈·CI 체크아웃 등으로
  이미 승인된 hook의 스크립트 파일이 재작성되는 상황. hook 정의 문자열(`command`)은 건드리지 않는다.
- **전제조건:**
  1. 프로젝트가 trusted 상태여야 project-local hook이 로드된다.
  2. 해당 hook이 과거에 한 번 승인되어 `trusted_hash`가 저장돼 있어야 한다.
  3. 공격자가 승인 이후 스크립트 파일 내용을 교체할 수 있어야 한다.

## [4] 근본 원인 (소스)

**[소스]** 신뢰 해시 계산 — `codex-rs/hooks/src/engine/discovery.rs`의 `hook_hash()`:

```rust
fn hook_hash(
    event_name: HookEventName,
    matcher: Option<&str>,
    group: &MatcherGroup,
    normalized_handler: HookHandlerConfig,
) -> String {
    // NormalizedHookIdentity { event_name, group(matcher + command 문자열 + 옵션) } 를
    // TOML 직렬화 후 해시. 참조 스크립트의 content/inode/digest는 포함하지 않는다.
}
```

**[소스]** 신뢰 판정 — 같은 파일 `hook_trust_status()`:

```rust
match trusted_hash {
    Some(trusted_hash) if trusted_hash == current_hash => HookTrustStatus::Trusted,
    Some(_) => HookTrustStatus::Modified,
    None    => HookTrustStatus::Untrusted,
}
```

`current_hash`가 스크립트 내용과 무관하므로, 스크립트를 교체해도 `trusted_hash == current_hash`가
유지되어 `Trusted`가 된다.

**[소스]** 실행 sink — `codex-rs/hooks/src/engine/command_runner.rs`의 `run_command()`:

```rust
#[cfg(not(windows))]
let child = command.spawn();   // 비샌드박스 직접 spawn
```

- unix에서 hook은 **command sandbox 없이** `tokio::process::Command::spawn()`으로 실행된다.
  (`#[cfg(windows)]`의 `spawn_contained`는 프로세스 트리 관리용 Windows JobObject일 뿐 샌드박스가 아니다.)
- 환경변수를 `env_clear()` 하지 않아 부모 프로세스 환경을 대부분 상속한다.

## [5] 획득 프리미티브 / 영향

- 사용자 승인 없는 **자동 실행**(이벤트 기반: SessionStart, PreToolUse 등).
- Codex command sandbox **밖**에서 실행 → repo 밖 파일 읽기/쓰기.
- **사용자 권한(same-user)** 프로세스 실행, 부모 환경변수 접근, 호스트 네트워크 접근 가능.
- SSH 키·클라우드 토큰·소스 트리 등 Codex 프로세스가 접근 가능한 자산으로 확대될 수 있어 영향 상한이 높다.

즉 이는 단순 "sandbox 내부 실행"이 아니라, **승인된 hook capability를 다른 코드로 재바인딩하는 host
same-user 코드 실행**이다.

## [6] 재현 및 증거 (5단)

### (1) 소스 — 0.147→0.148 diff
`hook_hash`가 참조 스크립트 내용을 제외하는 로직이 두 버전에서 동일(변경은 cosmetic). 최신에도 유효.

### (2) Unit test — 불변식 결정론적 확인 (rust-v0.148.0)

`codex-rs/hooks` 실제 discovery 코드로 "스크립트 내용 교체 → `current_hash` 불변 → `Trusted`"를 증명.

```bash
git clone --filter=blob:none https://github.com/openai/codex codex-src
cd codex-src && git checkout rust-v0.148.0
git apply repro-test.patch     # discovery.rs mod tests에 테스트 추가(첨부)
cd codex-rs
RUSTUP_TOOLCHAIN=stable cargo test -p codex-hooks \
  hook_trust_survives_target_script_content_substitution -- --nocapture
```

관찰:
```
test engine::discovery::tests::hook_trust_survives_target_script_content_substitution ... ok
test result: ok. 1 passed; 0 failed
```
- 스크립트를 benign→malicious로 교체해도 `current_hash` 동일 (`assert_eq!` 통과)
- `hook_trust_status(is_managed=false, current_hash_after, trusted_hash=hash_before)` == `Trusted`

### (3) E2E — sink 확인 (실제 0.148.0 바이너리)

trusted 프로젝트의 hook이 교체된 스크립트를 실제로 실행해 repo 밖 marker를 만듦.
(loopback mock Responses API로 turn을 완주시키고, SessionStart hook을 발화. `e2e-run.sh`/`e2e-mock.py` 첨부.)

```bash
bash e2e-run.sh SessionStart
```

관찰:
```
PWNED: hook executed the swapped script outside the repo:
  .../codex-hook-e2e/outside/HOOK_FIRED_SessionStart
  .../codex-hook-e2e/outside/whoami.txt
---
mjhy3
/home/mjhy3/agent/hunting-box/work/codex-hook-e2e/proj
```
repo **밖**에 marker 생성, `whoami`=사용자 본인(**same-user**), command sandbox 밖 실행 확인.

### (4) Faithful E2E — 승인 상태 직접 저장 + trust-bypass 없는 실행

승인 → 스크립트 교체 → **재승인 없이 실행**을 단일 실행으로 증명한다. `--dangerously-bypass-hook-trust`
를 쓰지 않는다.

```bash
bash poc-faithful.sh SessionStart
```

절차:
1. trusted 프로젝트에 benign hook 설정
2. **app-server `hooks/list`로 hook의 `key`+`currentHash` 획득** (= TUI가 승인 시 저장하는 값). 관찰:
   `key="<proj>/.codex/hooks.json:session_start:0:0"`, `currentHash="sha256:bd0fab40…"`, `trustStatus="untrusted"`
3. `CODEX_HOME/config.toml`에 `[hooks.state."<key>"] trusted_hash="<currentHash>"`를 직접 기록
   (= 실제 UI가 남기는 승인 상태를 시뮬레이션)
4. 공격자가 스크립트 **내용만** 교체 (hook 정의/문자열 불변)
5. **`codex exec` (bypass 없이)** → `currentHash`가 스크립트 내용과 무관하므로 여전히 `trusted_hash == currentHash`
   → hook이 `Trusted`로 발화

관찰:
```
PWNED (faithful): trusted-not-bypassed hook executed the SWAPPED script outside the repo:
  .../codex-hook-poc/outside/HOOK_FIRED_SessionStart
  .../codex-hook-poc/outside/whoami.txt
---
mjhy3
/home/mjhy3/agent/hunting-box/work/codex-hook-poc/proj
```

**승인된 hook의 스크립트를 교체했음에도 재승인 프롬프트 없이** command sandbox 밖에서 사용자 권한으로
실행됐다. 이 단계는 bypass 없는 실행을 확인하지만 승인 상태를 PoC가 직접 저장하므로, 실제 사용자 승인
경로에 대한 최종 증거는 다음 단계로 분리한다.

### (5) 실제 UI/API 승인 E2E — 완전한 체인 ★

`poc-real-approval-e2e.py`는 승인 상태를 직접 작성하지 않고 다음 두 승인 경로를 각각 시험한다.

```bash
./poc-real-approval-e2e.py --approval ui --codex /absolute/path/to/codex
./poc-real-approval-e2e.py --approval api --codex /absolute/path/to/codex
```

- `ui`: fresh `CODEX_HOME`의 startup hook review 화면에서 실제 `Trust all and continue` 항목을 PTY로
  선택한다.
- `api`: app-server `hooks/list`에서 얻은 `key`와 `currentHash`를 TUI와 같은
  `config/batchWrite(keyPath="hooks.state", mergeStrategy="upsert")` 요청으로 승인한다.

두 모드의 공통 관찰(최신 npm 안정 배포본):

```text
codex_version: codex-cli 0.148.0
binary sha256: ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074
before:         trustStatus=untrusted
after approval: trustStatus=trusted
after swap:     trustStatus=trusted, key/currentHash unchanged
bypass flag:    false
exec return:    0
marker:         observed outside project
whoami:         mjhy3
result:         PASS (UI), PASS (API)
```

같은 고정 바이너리로 각 승인 경로를 세 번씩 fresh 환경에서 반복한 결과도 안정적으로 분리됐다.

```text
UI:  3/3 PASS
API: 3/3 PASS
합계: 6/6 PASS
```

모든 run이 `Untrusted → Trusted → 스크립트 치환 후에도 Trusted`, `currentHash` 불변, outside marker
생성을 동일하게 관찰했다. 실행 환경과 개별 결과 SHA-256은 `STABILITY_EVIDENCE.md`에 첨부했다.

UI 승인도 내부적으로 app-server `config/batchWrite`를 사용한다. 공개 app-server에는 hook 전용
`approve` 메서드가 없으며, 이 config write가 Codex TUI가 구현한 실제 승인 API다. 승인 후 스크립트
내용만 바꿔도 `hooks/list`가 계속 `Trusted`를 반환하고, `--dangerously-bypass-hook-trust` 없는
`codex exec`에서 교체된 코드가 실행됐다. 따라서 "PoC가 승인 값을 임의로 주입했다"거나 "trust bypass
플래그 때문에 실행됐다"는 두 반론 모두 성립하지 않는다.

## [7] 정말 취약점인가

벤더가 "사용자는 파일 내용이 아니라 hook 경로/정의를 영구 신뢰한 것"이라 주장할 여지는 있다. 그러나
이 반론은 약하다: Codex는 스스로 **per-hook 신뢰 해시와 `Modified` 상태**를 구현해 "승인 이후 변경
감지"를 명시적으로 약속했고(app-server 문서도 `currentHash`/`trustStatus`가 승인 이후 변경 여부를
나타낸다고 설명), 정작 **실제 실행 내용의 변경만 감지하지 못한다**. 감지 기능이 존재하되 보안상 가장
중요한 대상을 커버하지 않는 것은 설계 동작이 아니라 무결성 검증 범위의 결함이다.

## [8] 심각도 판단

- 영향 상한: 승인 경계를 넘은 host same-user 코드 실행 → 자격증명·소스·토큰 유출/변조로 확대 가능(High).
- 익스플로잇 조건: trusted project + 과거 hook 승인 + 승인 후 스크립트 교체 능력.
- CVSS는 실제 배치 빈도(hook 사용률)·threat model 확인 전 확정하지 않는다. 제안 벡터(참고):
  `AV:L/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:H` 수준(공급망 전달 시 UI:R은 clone/pull 한 번).

## [9] 권고 (완화)

1. hook 신뢰 해시에 **참조 스크립트의 content digest**(및 resolved interpreter/binary, inode/device)를
   포함한다. 스크립트 내용이 바뀌면 해시가 바뀌어 `Modified` → 재승인.
2. 승인 시점의 스크립트 identity를 저장하고, 실행 직전 동일성을 검증(fail-closed)한다.
3. project-local hook(command·args·env·cwd·content hash)에 대해 trusted project라는 이유만으로 자동
   실행하지 말고 별도 승인 축을 둔다.
4. hook 프로세스를 최소 권한 sandbox와 제한된 environment·credential·network policy 안에서 실행한다.

## [10] 회귀 테스트

- 승인된 hook의 참조 스크립트 content 교체 후 재탐색 시 `Modified`로 바뀌는지.
- 해시가 command 문자열뿐 아니라 참조 파일 content/interpreter/inode 변화에 반응하는지.
- Linux·macOS·Windows 각각에서 hook 실행이 command sandbox 정책 하에 있는지.

## 첨부

- `repro-test.patch` — (2) unit test (rust-v0.148.0의 codex-rs/hooks/src/engine/discovery.rs에 적용)
- `e2e-run.sh`, `e2e-mock.py` — (3) E2E 드라이버 (loopback mock Responses API + marker 오라클)
- `poc-faithful.sh`, `poc-faithful-hooksclient.py` — (4) 직접 승인 상태 저장 + bypass 없는 실행
- `poc-real-approval-e2e.py` — (5) 실제 UI/API 승인 + 상태 재조회 + JSON 결과
- `repeat-real-approval-e2e.py`, `STABILITY_EVIDENCE.md` — UI/API 각 3회 반복 집계와 무결성 기록
- `README.md` — 재현 절차와 관찰 결과
