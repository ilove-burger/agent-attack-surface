# MCP Resource provenance 누락을 통한 durable Memory 오염과 cross-connector 유출

> **Provenance:** source commit `711a5f8b3a6eb40134146ae9ec22fdcdda5e3170`, 배포 CLI 0.147.0, 실제 모델과 합성 3-principal fixture로 독립 검증.
> **분석 상태:** `소스 확인` · `정상 TUI provenance bypass` · `natural phase-1` · `controlled phase-2/future-thread chain 1/1` · `hardening negative control`
> **시험한 보안 경계:** `disable_on_external_context=true`가 보장하는 Memory 제외 ≠ MCP Resource output/error에 실제 전달되는 provenance
> **판정:** 🔴 **LIVE primitive / 조건부 full-chain 후보** · OpenAI 제출 예정
> **OWASP ASI:** Primary **ASI06 Memory & Context Poisoning** · Chain ASI01, ASI02, ASI03
> **CWE(잠정):** CWE-345, CWE-668, CWE-200
>
> ⚠️ 실제 credential·SaaS·private data는 사용하지 않는다. full-chain은 합성 connector와 고유 canary만 사용한다.

## 결론

일반 MCP tool output은 외부 context로 표시되지만 `resources/read`, `resources/list`,
`resources/templates/list`의 공통 handler는 응답을 기본 provenance의 `FunctionToolOutput`으로 반환한다.
server-controlled error도 별도 model-visible 경로로 들어간다. 그 결과
`memories.disable_on_external_context=true`인데도 해당 thread가 `enabled`로 남고 Memory phase-1 대상이 된다.

정상 TUI에서는 DB·rollout·clock 수정 없이 Resource marker가 natural phase-1에 저장되는 것을 확인했다.
별도 controlled full-chain에서는 attacker issue runbook이 phase-2 summary에 들어간 뒤, source가 없는 future
thread가 private registry canary를 public observer request argument로 전달했다.

## 증거 계층

| 계층 | 관찰 | 판정 |
|---|---|---|
| unit reproduction | Resource read 후 `memory_mode=enabled`, phase-1 claim 가능 | 결정론적 PASS |
| normal TUI | read/list/template/error 모두 enabled; hardening은 polluted | PASS |
| natural idle | actual model phase-1이 Resource-derived marker를 방어적 기록으로 보존 | PASS |
| clean baseline | Memory 없는 future thread는 registry/observer를 호출하지 않음 | 0/1 |
| controlled full-chain | persisted runbook이 registry→observer exact canary 전송 | 1/1 |
| call-time hardening | source 단계에서 polluted, 대상 phase-1 output 없음 | 1/1 차단 |

## 재현

결정론적 root-cause test:

```bash
./run-tests.sh /absolute/path/to/openai-codex-checkout
```

세 principal fixture 자체 검사:

```bash
python3 full-chain/verify_fixture.py
```

## 중요한 제한

- 정상 TUI natural flow는 Resource→enabled→phase-1 persistence까지 확인했다. 해당 실행의 phase-2는 host
  bubblewrap 제약으로 실패했다.
- 공격자 선택 runbook→phase-2→future cross-connector chain은 eligibility metadata와 retry timing을
  통제한 연구 환경에서 1/1이다. typical deployment 성공률을 주장하지 않는다.
- observer는 read-only지만 request argument가 원격 log에 남는 confidentiality sink로 모델링됐다.
- 실제 SaaS tenant나 제3자 credential 유출은 수행하지 않았다.

## Files

- [`DISCLOSURE.md`](DISCLOSURE.md) — 상세 제출 보고서
- [`reproduction-test.patch`](reproduction-test.patch) — live primitive 결정론적 test
- [`proposed-hardening.patch`](proposed-hardening.patch) — call-time negative control
- [`phase1-persistence-test.patch`](phase1-persistence-test.patch), [`phase2-consolidation-test.patch`](phase2-consolidation-test.patch) — pipeline edge tests
- [`run-tests.sh`](run-tests.sh) — guarded scoped-test runner
- [`full-chain/`](full-chain/) — source/registry/observer fixture와 self-check
- [`evidence/`](evidence/) — 정상 TUI, natural stage-1, controlled full-chain 증거

