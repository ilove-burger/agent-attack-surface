# GNU sed suffix가 persistent prefix approval을 unsandboxed command execution으로 확장

> **Provenance:** Codex CLI 0.147.0 full impact와 0.148.0 policy oracle, GNU sed 4.9에서 독립 재현.
> **분석 상태:** `소스 확인` · `policy-only 0.147/0.148` · `marker E2E 0.147` · `loopback impact 확인`
> **시험한 보안 경계:** 화면에 표시된 고정 read command의 승인 범위 ≠ 같은 argv prefix 뒤에 추가 가능한 실행 capability
> **판정:** 🔴 **LIVE (0.148.0 policy 재현, 미패치 후보)** · OpenAI 제출 예정
> **OWASP ASI:** Primary **ASI05 Unexpected Code Execution** · Secondary ASI02 Tool Misuse & Exploitation
> **CWE:** Primary CWE-88 · Impact CWE-78
>
> ⚠️ 공개·재배포 전 벤더 조정 필요. 첨부 PoC는 policy-only 또는 disposable marker만 사용한다.

## 결론

Codex가 고정 파일을 읽는 GNU `sed` argv를 reusable prefix로 영구 승인하면, 미래 명령의 후행 argv는
rule match의 부정 조건이 아니다. GNU sed는 입력 파일 뒤에서도 `-e`를 옵션으로 해석하며 `e` command는
shell을 호출한다. 따라서 같은 prefix 뒤에 literal `-e` program을 붙이면 새 승인 없이 allow되고,
prefix-rule escalation 경로가 이를 command sandbox 밖에서 실행할 수 있다.

## 최소 정책 재현

```bash
./run-policy-check.sh /absolute/path/to/codex
```

성공 조건:

1. candidate 전체 argv의 최종 decision이 `allow`다.
2. `matchedPrefix`는 고정 파일 경로에서 끝난다.
3. appended `-e '1e /usr/bin/id'`는 matched prefix 밖에 있다.
4. 다른 입력 경로 negative control은 allow되지 않는다.

0.148.0 binary SHA-256 `ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074`에서
policy-only candidate가 다시 `allow`로 확인됐다.

## 획득 프리미티브

선행 영구 승인 한 번 뒤, 추가 승인 없는 same-user host command execution이다. 확인된 안전한 영향은
`/usr/bin/id`, workspace 밖 marker, 연구자 소유 loopback callback이다. callback payload는 제출물에서
제외한다.

## 전제와 비주장

- suffix를 허용하는 reusable sed prefix approval이 먼저 존재해야 한다.
- 모든 sed 명령이나 모든 Codex 세션이 자동으로 취약하다는 주장이 아니다.
- policy oracle은 0.148.0까지 확인했지만 full marker E2E 기록은 0.147.0 기준이다.
- 결과는 Codex sandbox/approval escape이며 OS privilege escalation이 아니다.

## Files

- [`DISCLOSURE.md`](DISCLOSURE.md) — 상세 제출 보고서
- [`run-policy-check.sh`](run-policy-check.sh) — candidate/negative-control 자동 판정
- [`poc/policy.rules`](poc/policy.rules) — harmless fixed-read prefix rule
- [`poc/input.txt`](poc/input.txt) — fixture
- [`evidence/policy-0.148.0.json`](evidence/policy-0.148.0.json) — 0.148.0 실제 출력
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md) — E2E와 한계

