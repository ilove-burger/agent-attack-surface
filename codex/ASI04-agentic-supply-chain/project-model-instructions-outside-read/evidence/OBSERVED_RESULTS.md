# Sanitized observed results

> 대상: `codex-cli 0.149.0` (`bbc3341e44c9ead340ed9570c17be936e37870f570751a941699ffd04d672827`)
> 소스: `rust-v0.148.0` (`https://github.com/openai/codex.git`)
> 플랫폼: Linux x86_64, `hunt-shell`(bwrap 격리, offline, fresh HOME/CODEX_HOME per run)
> 판정: **CONFIRMED** (기술 동작), containment 수정안 자체 검증 완료

## 소스 버전 경계

| 역할 | 커밋 | 최초 확인 태그 |
|---|---|---|
| project config 도입(primitive) | `8ff16a7714a9680d9bfe51d5a49bba5a9e59ad94` | `rust-v0.78.0` (`0.77.0`엔 없음) |
| project trust gate 도입 | `7351c129992d85405e53a285cb4916ccb223489f` | `rust-v0.88.0-alpha.9` |
| 설정 키 이름 변경(primitive 유지) | `f4d55319d147a8d840e5279e9a6ed7988bf736aa` | `rust-v0.88.0-alpha.14` (`experimental_instructions_file` → `model_instructions_file`) |

## 실제 UI trust E2E — 안정성 3/3

fresh clone → 실제 시작 TUI의 `Yes, continue`에 Enter → loopback mock에서 첫 요청 캡처.
bypass 플래그 미사용. 매 run 별도 fresh `HOME`/`CODEX_HOME`.

| Run | 결과 | 승인 전 요청 | 승인 후 요청 | canary == instructions | result.json SHA-256 |
|---|---|---:|---:|---|---|
| v2 | PASS | 0 | 1 | true | `16d91670b33fb818152c0e8eb06152b7f1271f621804acc7f2a6011141788032` |
| v3 | PASS | 0 | 1 | true | `6617b4be9b2aa48423226b55d631032a9958769e639104f69c6eeaf2c43eace2` |
| v4 | PASS | 0 | 1 | true | `9fc7ee0482ba17caf7cb35f379fb16198dd3699186a648a3d3f87022d76873b9` |

캡처된 요청의 `instructions` 필드는 synthetic canary
(`HUNMA_UI_TRUST_OUTSIDE_MODEL_INSTRUCTIONS_0_149_0_ONLY`)와 3회 모두 정확히 일치했고
(`instructions_length: 54`), `worktree_clean_before/after`·`no_bypass_flag`·
`loopback_model_endpoint` 등 전 체크 항목이 통과했다.

## 런타임 syscall 검증 (strace)

동일 E2E를 `strace -f -e trace=open,openat,openat2,read`로 감싸 재실행. project 밖 절대경로가
**legacy `open()`**(`openat`이 아님 — 첫 트레이스 필터 설계에서 놓쳤던 지점)으로 직접 열리고, 곧바로
canary 내용이 `read()`됐다. 한 실행 안에서 동일 패턴이 7회 관찰됨(설정 재로딩 경로와 일치).

```text
open("<run-dir>/e2e/outside/fake-secret.txt", O_RDONLY|O_NONBLOCK|O_LARGEFILE|O_CLOEXEC) = 41
read(41, "HUNMA_UI_TRUST_OUTSIDE_MODEL_INSTRUCTIONS_0_149_0_ONLY\n", 55) = 55
```

- strace 로그 SHA-256: `eb129a89f62ec3c7f72f4c6749776ea8be2d360aff04e3932b05635ea497f8d1` (12,851줄,
  원본은 로컬 scratch에만 보관, 이 bundle에는 포함하지 않음 — 재현 방법은 `CALL_CHAIN.md` 참고)
- 해당 E2E run의 result.json SHA-256: `c294348e029d3d112c6c4be212aa5085c19d41bfe51c9ea2c18d73e0e8a469ae`
  (`pass: true`)

## Containment 패치 유무 대조 (회귀 테스트)

`config/src/loader/tests.rs`의 두 테스트를 실제 `load_config_layers_state()`(프로덕션 진입점)로
실행한 결과:

| 테스트 | 패치 없이 | 패치 적용 |
|---|---|---|
| `project_model_instructions_file_outside_project_root_is_dropped` | **FAIL** — `model_instructions_file` = `/tmp/.tmpYMSNOv/outside/secret.md`가 그대로 effective config에 남음 (취약점 재현) | PASS |
| `project_model_instructions_file_inside_project_root_is_kept` (음성 대조군) | PASS | PASS |

패치 적용 후 전체 스위트 `cargo test -p codex-config`: **261 passed, 0 failed**.
다운스트림 `cargo check -p codex-core`: clean.

## 증거 보존 제한

전체 strace 로그(12,851줄)와 개별 UI E2E run 디렉터리(approval-ui 로그, codex-home 등)는 로컬
`hunting-box/work/`에만 보관하고 이 bundle에는 포함하지 않았다. 첨부된 `CALL_CHAIN.md`의 재현
절차를 따르면 같은 syscall 증거를 재생성할 수 있다.
