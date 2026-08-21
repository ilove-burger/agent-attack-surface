# direct full-network sandbox에서 App Server Unix control socket을 통한 same-user RCE

> **Provenance:** Codex CLI 0.147.0 source 분석, Docker 조건 행렬, Ubuntu kernel VM UID 1000 E2E로 독립 재현.
> **분석 상태:** `소스 확인(rust-v0.147.0)` · `baseline` · `network 행렬` · `비특권 동일 UID full chain`
> **시험한 보안 경계:** internet network 허용 ≠ host-local privileged IPC 접근 권한
> **판정:** 🔴 **LIVE (조건부 0-day 후보)** · OpenAI 제출 예정
> **OWASP ASI:** Primary **ASI05 Unexpected Code Execution** · Secondary ASI02, ASI03
> **CWE(잠정):** CWE-284, CWE-441, CWE-749, CWE-653
>
> ⚠️ PoC는 연구자 소유 Unix socket과 marker만 사용한다. 임의 외부 서비스나 credential에 접근하지 않는다.

## 결론

Linux direct full-network profile에서 managed proxy가 꺼져 있으면 network seccomp가 설치되지 않아
AF_UNIX도 허용된다. 같은 UID의 Codex App Server control socket은 mode `0600`만 적용할 뿐 connection
capability나 sandbox trust level을 인증하지 않는다. 따라서 sandboxed process가 WebSocket JSON-RPC로
연결해 `fs/writeFile` 또는 unsandboxed `process/spawn`을 호출하고 filesystem sandbox를 우회할 수 있다.

## 공격 흐름

```text
workspace-restricted filesystem + direct full-network
  → network seccomp omitted
  → same-UID AF_UNIX connect
  → unauthenticated App Server WebSocket initialization
  → client declares experimentalApi=true
  → process/spawn or fs/writeFile
  → App Server authority writes outside workspace
```

## 조건 행렬

| sandbox 조건 | AF_UNIX | outside marker |
|---|---:|---:|
| restricted `:workspace` | EPERM | 없음 |
| full-network, proxy off | 성공 | 생성 |
| full-network + socket deny, proxy off | 성공 | 생성 |
| full-network, managed proxy on | EPERM | 없음 |

Ubuntu VM의 실제 App Server, socket, client, marker는 모두 UID/GID 1000이었다. direct outside write는
EROFS로 실패했지만 `process/spawn`을 통한 marker write는 성공했다.

## 재현

```bash
./run-e2e.sh --codex /absolute/path/to/codex
```

Runner는 isolated `CODEX_HOME`에서 Unix listener를 시작한 뒤 restricted negative control, direct-write
baseline, full-network candidate를 순서대로 실행한다. Host가 unprivileged user namespace를 차단하면
결과를 실패로 오인하지 않고 해당 환경 제약을 보고해야 한다.

## 전제와 비주장

- Linux, direct full-network, proxy off, 동일 UID App Server listener가 동시에 필요하다.
- 기본 restricted profile에서는 재현되지 않았다.
- App Server listener가 모든 기본 TUI 환경에서 항상 실행된다고 주장하지 않는다.
- 이는 Codex sandbox escape이며 UID, VM 또는 container 경계 탈출이 아니다.

## Files

- [`DISCLOSURE.md`](DISCLOSURE.md) — 상세 제출 보고서
- [`poc_uds_client.py`](poc_uds_client.py) — dependency-free Unix WebSocket JSON-RPC client
- [`run-e2e.sh`](run-e2e.sh) — 대조군과 marker oracle runner
- [`evidence/OBSERVED_RESULTS.md`](evidence/OBSERVED_RESULTS.md) — UID 1000 및 조건 행렬 증거

