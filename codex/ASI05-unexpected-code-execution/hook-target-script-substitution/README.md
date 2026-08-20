# 승인된 project hook의 대상 스크립트 치환 → sandbox-외부 same-user 코드 실행

> **Provenance:** 이 워크스페이스에서 소스 분석 + unit test + E2E로 독립 재현 (OpenAI Codex CLI, 0.148.0).
> **분석 상태:** `소스 확인(rust-v0.148.0)` · `unit test 재현` · `E2E sink 재현` · `Faithful E2E 재현(bypass 없이)`
> **시험한 보안 경계:** 승인된 hook의 trust 해시가 커버하는 대상 ≠ 실제 실행되는 스크립트 파일의 내용
> **판정:** 🔴 **LIVE (미패치 0-day 후보)** · **제보:** 진행 예정 (OpenAI Codex). 상위 [카테고리 인덱스](../README.md) · repo 루트 [README](../../../README.md).
> **OWASP ASI:** Primary **ASI05 Unexpected Code Execution (RCE)** · Secondary ASI02 Tool Misuse & Exploitation
> **CWE(잠정):** CWE-345 (Insufficient Verification of Data Authenticity), 관련 CWE-353
>
> ⚠️ 미패치 이슈. 공개·재배포 금지. PoC는 marker-only(touch/whoami), 무기화 없음.

## 요약

Codex는 project hook의 신뢰 상태를 hook **정의**(event/matcher/command 문자열)의 해시로만 판정하고,
command가 참조하는 **스크립트 파일의 내용**은 해시에 포함하지 않는다. 따라서 한 번 승인된 hook의
스크립트 내용을 out-of-band로 교체하면, 신뢰 해시가 불변이라 재승인 없이 `Trusted`로 남고, 이벤트
발생 시 교체된 스크립트가 **command sandbox 밖에서 사용자 권한으로** 실행된다.

## 가설

> 사용자가 한 번 승인한 project hook의 대상 스크립트를, 공격자가 hook 정의는 그대로 두고 **내용만**
> 교체하면, Codex가 재승인 없이 그 스크립트를 실행하는가?

## 근본 원인 (소스, rust-v0.148.0)

`hook_hash()` — `codex-rs/hooks/src/engine/discovery.rs`: `NormalizedHookIdentity{event, matcher,
command 문자열}`만 TOML 직렬화해 해싱. 참조 스크립트의 content/inode/digest는 제외.

`hook_trust_status()`: `trusted_hash == current_hash` 면 `Trusted`, 다르면 `Modified`. `current_hash`가
스크립트 내용과 무관하므로 스크립트를 교체해도 `Trusted` 유지.

sink — `command_runner.rs`: unix에서 `#[cfg(not(windows))] command.spawn()` (비샌드박스), `env_clear()`
안 함(부모 환경 상속). `spawn_contained`는 Windows JobObject 전용이라 샌드박스 아님.

0.147→0.148 diff는 cosmetic — 해시 로직 불변. 최신에도 유효.

## 공격 흐름

```
사용자:  .codex/hooks.json 의 hook "sh ./hooks/check.sh" 를 한 번 승인
Codex:   current_hash(정의) 를 trusted_hash 로 저장
공격자:  hook 문자열은 그대로, check.sh "내용만" 악성으로 교체 (clone/pull/파일쓰기)
Codex:   재탐색 → current_hash 불변 → Trusted → 이벤트 시 교체된 스크립트 자동 실행
```

## 획득 프리미티브

- 사용자 승인 없는 자동 실행(이벤트 기반), command sandbox **밖** same-user 실행
- 부모 환경변수 상속, repo 밖 파일 읽기/쓰기, 호스트 네트워크 접근 가능
- 즉 승인된 hook capability를 다른 코드로 재바인딩하는 **host same-user RCE**

## 증거 (4단)

| 단계 | 증거 | 결과 |
|---|---|---|
| 1. 소스 | `hook_hash`가 스크립트 content 제외 (0.147→0.148 diff cosmetic) | 최신 LIVE |
| 2. Unit test | 실제 `codex-hooks` 코드로 content 교체 → `current_hash` 불변 → `Trusted` | `1 passed` |
| 3. E2E sink | trusted 프로젝트 hook이 교체 스크립트를 repo 밖 same-user 실행 (bypass) | `PWNED` |
| 4. **Faithful E2E** | **bypass 없이** 승인→교체→재승인 없이 실행 | `PWNED (faithful)` |

**4단계(결정적):** app-server `hooks/list`로 얻은 `currentHash`를 `trusted_hash`로 저장(=승인) → 스크립트
교체 → `codex exec`(bypass 없이) → 여전히 `Trusted`로 발화 → repo 밖 marker(same-user). 실제 신뢰
플로우만으로 성립하므로 "trust를 우회했다"는 반론이 성립하지 않는다.

## 정말 취약점인가

Codex가 스스로 per-hook 신뢰 해시와 `Modified` 상태를 구현해 "승인 이후 변경 감지"를 약속했음에도,
보안상 가장 중요한 **실제 실행 내용의 변경**만 감지하지 못한다. 감지 기능이 존재하되 핵심 대상을
커버하지 않는 것은 설계 동작이 아니라 무결성 검증 범위의 결함이다.

## 완화 (권고)

1. 신뢰 해시에 **참조 스크립트 content digest**(+ resolved interpreter/binary, inode/device) 포함
2. 실행 직전 스크립트 identity 동일성 검증(fail-closed)
3. project-local hook을 trusted project라는 이유만으로 자동 실행하지 말고 별도 승인 축
4. hook 프로세스를 최소 권한 sandbox + 제한된 env/credential/network 하에서 실행

## Files (이 폴더)

- [`DISCLOSURE.md`](DISCLOSURE.md) — 전체 제보서 초안(개요·불변식·벡터·근본원인·4단 증거·완화)
- [`repro-test.patch`](repro-test.patch) — (2) unit test (codex-rs/hooks discovery.rs에 적용)
- [`poc-faithful.sh`](poc-faithful.sh) + [`poc-faithful-hooksclient.py`](poc-faithful-hooksclient.py) — (4) **faithful PoC** (bypass 없음)
- [`e2e-run.sh`](e2e-run.sh) + [`e2e-mock.py`](e2e-mock.py) — (3) E2E sink PoC + mock Responses API

## 재현 (요약)

```bash
# 핵심 취약점(불변식):
git clone --filter=blob:none https://github.com/openai/codex codex-src
cd codex-src && git checkout rust-v0.148.0 && git apply <이 폴더>/repro-test.patch
cd codex-rs && RUSTUP_TOOLCHAIN=stable cargo test -p codex-hooks \
  hook_trust_survives_target_script_content_substitution
#   → test result: ok. 1 passed

# 완전한 체인(faithful, bypass 없이): 경로/바이너리는 환경에 맞게 조정
bash <이 폴더>/poc-faithful.sh SessionStart
#   → PWNED (faithful): ... executed the SWAPPED script outside the repo
```

> PoC 스크립트는 codex 0.148.0 바이너리 경로와 절대경로를 환경에 맞게 수정해서 쓴다. proj를 독립
> project-root로 만들기 위해 `git init` 하는 것이 관건(상위 `.git`가 hook 로드를 가로채지 않도록).
