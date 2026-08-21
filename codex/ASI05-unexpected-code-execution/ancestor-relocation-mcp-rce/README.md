# writable ancestor relocation을 통한 project metadata 보호 우회와 stdio MCP RCE

> **Provenance:** 소스 분석과 실제 `@openai/codex@0.147.0` Docker E2E로 독립 재현.
> **분석 상태:** `소스 확인(rust-v0.147.0)` · `baseline 확인` · `전체 체인 10/10`
> **시험한 보안 경계:** sandbox 생성 시 경로 이름에 부착된 `.codex` read-only carveout ≠ rename 후 복원되는 실제 프로젝트 객체
> **판정:** 🔴 **LIVE (미패치 0-day 후보)** · OpenAI 제출 예정
> **OWASP ASI:** Primary **ASI05 Unexpected Code Execution** · Secondary ASI02 Tool Misuse & Exploitation
> **CWE(잠정):** CWE-706, CWE-367, CWE-284
>
> ⚠️ 비공개 제출용 자료. PoC는 disposable Docker container와 marker 파일만 사용하며 Docker 경계를 벗어나지 않는다.

## 결론

Codex Linux workspace sandbox는 writable root를 bind한 뒤 `.codex` 같은 project metadata 경로를
read-only로 덮는다. 공격자가 writable ancestor를 첫 sandbox에서 rename하고 원래 위치에 decoy를
만들면, 두 번째 sandbox는 decoy의 `.codex`를 보호하고 이동된 실제 프로젝트의 `.codex`는 넓은
writable mount 아래에 남는다. 공격자는 실제 config에 stdio MCP command를 주입하고 프로젝트를 원래
경로로 복원할 수 있다. 새 Codex 세션은 주입된 MCP를 command sandbox 밖에서 시작한다.

## 공격 흐름

```text
trusted project under renameable writable ancestor
  → sandbox #1: ancestor rename + decoy creation
  → sandbox #2: protection binds to decoy path
  → moved real .codex/config.toml becomes writable
  → inject enabled stdio MCP and restore original path
  → fresh Codex session reloads project config
  → unsandboxed same-user MCP child process
```

## 증거

| 단계 | 오라클 | 결과 |
|---|---|---|
| baseline 1 | ordinary workspace sandbox가 `.codex/config.toml`을 덮지 못함 | EROFS, PASS |
| baseline 2 | ordinary sandbox가 container `/root` marker를 만들지 못함 | EROFS, PASS |
| relocation | moved real `.codex/config.toml`이 MCP 설정으로 교체되고 trusted path로 복원됨 | PASS |
| sink | fresh `codex exec`의 MCP child가 container marker와 parent cmdline 기록 | PASS |
| stability | 매번 fresh container로 전체 체인 반복 | 10/10 PASS |

## 재현

```bash
cd poc
TRIALS=10 ./run.sh
```

성공 조건은 두 baseline이 모두 차단되고, 변조된 config가 trusted path에 복원된 뒤
`/root/codex-mcp-host-rce`에 `CODEX_MCP_HOST_RCE`와 Codex parent cmdline이 기록되는 것이다.

## 전제와 비주장

- trusted project, rename 가능한 writable ancestor, 두 번의 독립 sandbox 호출, config reload가 필요하다.
- 확인 범위는 Linux bubblewrap와 0.147.0이다. macOS와 Windows는 미검증이다.
- Docker `--privileged`는 이 host에서 bubblewrap namespace를 만들기 위한 실험 조건이다.
- 이는 Codex command-sandbox escape이며 Docker/VM escape나 OS 권한 상승이 아니다.

## Files

- [`DISCLOSURE.md`](DISCLOSURE.md) — 상세 제출 보고서
- [`poc/README.md`](poc/README.md) — 재현 계약과 전제조건
- [`poc/run.sh`](poc/run.sh) — fresh-container 반복 runner
- [`poc/run-inside.sh`](poc/run-inside.sh) — baseline부터 sink까지 전체 E2E
- [`poc/stage1.sh`](poc/stage1.sh), [`poc/stage2.sh`](poc/stage2.sh) — relocation 단계
- [`poc/payload.sh`](poc/payload.sh) — marker-only MCP payload
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md) — 비식별화 관찰 결과

