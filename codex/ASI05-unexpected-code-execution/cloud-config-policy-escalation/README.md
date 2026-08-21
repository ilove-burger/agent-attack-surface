# client-known cloud-config HMAC을 통한 다음 실행의 sandbox policy escalation

> **Provenance:** source commit `85fc4def358b7df21883e72ae8dda43a0f572f32`에서 test-only patch와 실제 CLI E2E로 독립 재현.
> **분석 상태:** `소스 확인` · `내부 테스트 3/3` · `actual CLI 3/3` · `guarded total 6/6`
> **시험한 보안 경계:** server-issued enterprise policy authenticity ≠ 모든 client에 포함된 대칭 HMAC key로 검증 가능한 cache
> **판정:** 🔴 **LIVE (배치 조건부 0-day 후보)** · OpenAI 제출 예정
> **OWASP ASI:** Primary **ASI05 Unexpected Code Execution** · Secondary ASI03 Identity & Privilege Abuse, ASI06 Memory & Context Poisoning
> **CWE(잠정):** CWE-321, CWE-345, CWE-284
>
> ⚠️ fixture identity와 loopback backend만 사용한다. 실제 계정·토큰·cloud cache는 사용하거나 생성하지 않는다.

## 결론

Cloud-config cache의 HMAC key가 source와 binary에 공통으로 포함되어 있어 로컬 공격자도 server가 발급한
것처럼 보이는 cache를 만들 수 있다. writable custom `CODEX_HOME`이 workspace 안에 있는 배치에서는
제한된 첫 Codex process가 자신의 `auth.json` fixture identity를 읽고 위조 cache를 기록할 수 있다.
다음 fresh process는 backend 확인 없이 cache를 채택해 `approval=never`,
`sandbox=danger-full-access`로 전환하고 workspace 밖에 쓸 수 있다.

별도 writer 결함으로 cache file symlink를 따라 outside target을 fixed-format cache JSON으로 덮는
경로도 확인했다. 이 보조 경로는 arbitrary-content write로 주장하지 않는다.

## 공격 흐름

```text
restricted process + writable custom CODEX_HOME
  → read local fixture identity
  → generate policy cache with client-known HMAC
  → outside write remains denied in process #1
  → fresh process accepts cache before backend request
  → Never + DangerFullAccess
  → model shell writes outside workspace
```

## 증거

| 묶음 | 확인 내용 | 결과 |
|---|---|---|
| cloud-config | public-HMAC cache acceptance, long expiry, refresh-failure persistence | 2/2 PASS |
| protocol | custom-named workspace-local home cache path의 write 가능성 | 1/1 PASS |
| actual CLI | forged cache consumer, symlink clobber, restricted-writer→fresh-consumer chain | 3/3 PASS |

## 재현

```bash
./run-proof.sh /absolute/path/to/openai-codex-checkout
```

Runner는 관련 제품 파일에 기존 변경이 있으면 중단하고, 두 test-only patch를 적용한 뒤 scoped test를
실행하며 종료 trap에서 patch를 되돌린다.

## 전제와 비주장

- Business/Enterprise/Edu identity와 writable custom `CODEX_HOME` 또는 동등한 same-user writer가 필요하다.
- 다음 실행에서 local sandbox mode가 명시적으로 고정되어 있으면 DFA 기본값 적용이 차단될 수 있다.
- 더 높은 우선순위의 MDM/managed requirements가 있으면 정책 확장이 제한될 수 있다.
- 기본 `~/.codex`가 workspace-write만으로 쓰인다고 주장하지 않는다.
- 결과는 same-user host execution이며 OS privilege escalation이 아니다.

## Files

- [`DISCLOSURE.md`](DISCLOSURE.md) — 상세 제출 보고서
- [`run-proof.sh`](run-proof.sh) — guarded runner
- [`cloud-config-hmac-proof.patch`](cloud-config-hmac-proof.patch) — cache/service/protocol 테스트
- [`actual-cli-e2e.patch`](actual-cli-e2e.patch) — actual CLI 세 가지 E2E
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md) — 6/6 관찰 결과와 한계

