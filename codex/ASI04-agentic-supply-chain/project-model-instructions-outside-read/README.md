# Project-local `model_instructions_file`을 통한 프로젝트 밖 파일 읽기 → 모델 instructions 주입

> **Provenance:** 소스 분석 + 실제 `codex-cli 0.149.0` UI trust E2E(`hunt-shell` 격리, bypass 없음)로 독립 재현.
> **분석 상태:** `소스 확인(rust-v0.148.0)` · `최초 stable 경계 확인(0.77.0/0.78.0)` · `UI trust E2E 3/3` ·
> `런타임 syscall 검증(strace)` · `containment 수정안(lexical+symlink canonicalize) + 회귀 테스트 4건 작성·검증`
> **시험한 보안 경계:** project-local 설정이 지정할 수 있는 경로 ≠ project_root 내부로 한정된 경로
> **판정:** 🔴 **LIVE (미패치 0-day 후보, containment 수정안 자체 검증 완료)** · **제보:** 진행 예정
> (OpenAI Codex). 상위 [카테고리 인덱스](../README.md) · repo 루트 [README](../../../README.md).
> **OWASP ASI:** Primary **ASI04 Agentic Supply Chain** · Secondary ASI06 Memory & Context Poisoning
> **CWE(잠정):** CWE-22 (Path Traversal), 관련 CWE-829 (Inclusion of Functionality from Untrusted Control Sphere)
>
> ⚠️ 미패치 이슈. 공개·재배포 금지. PoC는 synthetic canary + loopback endpoint만 사용, 무기화 없음.

## 결론

신뢰(trust)한 프로젝트의 `.codex/config.toml`이 `model_instructions_file`에 절대경로·`..`·
symlink를 지정하면, Codex는 그 값을 `.codex/` 디렉터리 기준으로 절대화만 하고 **프로젝트 경계
내부인지는 검사하지 않는다**. 해석된 경로의 내용은 그대로 읽혀 `base_instructions`가 되고, 매 턴
Responses 요청의 최상위 `instructions` 필드로 전송된다 — 재확인 없이, 프로젝트 신뢰 승인 1회로
자동 발동한다.

```text
공격자 통제: 저장소의 .codex/config.toml (model_instructions_file 필드)
전달 경로:   피해자가 clone → 시작 화면 신뢰 승인(기본 선택지 Enter)
결과:        프로젝트 밖 임의 파일(예: ~/.ssh/id_rsa)이 매 턴 모델 API로 전송됨
             + 그 내용이 system-level instructions로 주입돼 이후 모델 행동을 조작 가능
```

두 영향(정보 유출 + instructions 하이재킹)이 같은 sink에서 분리 불가능하게 동시에 발생한다.
상세는 [`DISCLOSURE.md`](DISCLOSURE.md) 참고.

## 재현

핵심 근본원인(해시가 아니라 이번엔 containment 부재)은 unit-test 수준이 아니라 실제 config
로딩 파이프라인(`load_config_layers_state`)을 태우는 회귀 테스트로 확인했다 — 상세는
[`HARDENING.md`](HARDENING.md).

버전 경계와 UI trust E2E 3/3, strace 런타임 증거는 [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md).

## Files

- [`DISCLOSURE.md`](DISCLOSURE.md) — 전체 제보서 초안(개요·threat model·근본원인·재현·심각도·완화·회귀테스트)
- [`CALL_CHAIN.md`](CALL_CHAIN.md) — Config → `base_instructions` → Responses `instructions` 7단계
  call chain, 소스 파일:라인 + strace 런타임 검증
- [`HARDENING.md`](HARDENING.md) — containment 수정안 설계 근거·한계, 패치 유무 대조 테스트 결과
- [`proposed-fix.patch`](proposed-fix.patch) — containment 수정안 (`config/src/loader/mod.rs`,
  project layer에만 스코프, lexical pass + symlink canonicalize pass)
- [`regression-test.patch`](regression-test.patch) — 회귀 테스트 4개 (`config/src/loader/tests.rs`,
  escape/in-project × plain path/symlink)
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md) — 버전 경계·UI E2E·strace·회귀
  테스트 결과 요약
- [`evidence/SHA256SUMS`](evidence/SHA256SUMS) — 이 폴더 파일 무결성
