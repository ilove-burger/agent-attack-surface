# Sanitized observed results

> 증거 유형: 2026-08-18 로컬 실행에서 보존한 비식별화 요약
> 대상: `@openai/codex@0.147.0`, source `be6e8eac029b183056b7e4402879f15d2c85f61b`
> 환경: disposable Alpine-based Docker container, Linux bubblewrap
> 반복: fresh container 10회
> 판정: **10/10 PASS**

## 공통 오라클

```text
PASS: ordinary sandbox write was denied
PASS: ordinary sandbox also cannot write the host-only /root marker
PASS: moved real .codex/config.toml was overwritten and restored to the trusted path
[5/5] SUCCESS
parent_cmdline: .../bin/codex exec --ephemeral ...
All 10 fresh-container trial(s) passed.
```

각 run은 새 container에서 시작했다. `payload.sh`는 container 내부
`/root/codex-mcp-host-rce`에 UID, PID, PPID, cwd, parent cmdline만 기록한다.

## 해석 범위

- 첫 두 baseline은 ordinary workspace sandbox의 metadata 및 outside marker 보호가 실제로 활성화됐음을 보인다.
- relocation 후 config 교체만으로는 최종 판정하지 않고, fresh Codex가 주입된 MCP child를 시작한 marker까지 요구했다.
- Docker 밖 host path, 외부 network, credential은 사용하지 않았다.
- 원본 container log와 image는 이 bundle에 포함하지 않았다. 첨부 runner가 동일 oracle을 새 container에서 재생성한다.

