# Sanitized observed results

> 대상: `codex-cli 0.147.0`
> source: `be6e8eac029b183056b7e4402879f15d2c85f61b`
> 플랫폼: Docker 조건 행렬 + Ubuntu `7.0.0-28-generic` VM
> 공격 process/App Server/socket/marker: UID/GID 1000
> 판정: **same-UID full-network chain CONFIRMED**

## 조건 행렬

| 조건 | socket connect | marker |
|---|---|---|
| restricted `:workspace` | `EPERM` | absent |
| full-network, proxy off | success | present |
| full-network + socket deny, proxy off | success | present |
| full-network, managed proxy on | `EPERM` | absent |

## 비특권 VM baseline

```text
uid=1000(node) gid=1000(node)
uid=0(root) gid=0(root)   # unshare -Ur namespace 내부
unshare_rc=0

/bin/sh: can't create /home/node/host-marker: Read-only file system
sandbox_rc=1
BASELINE_DENIED
```

## Candidate transcript excerpt

```json
{"id":1,"result":{"userAgent":"nonroot-poc/0.147.0 ...","codexHome":"/home/node/.codex","platformOs":"linux"}}
{"id":2,"result":{}}
{"method":"process/exited","params":{"processHandle":"poc","exitCode":0}}
```

```text
client_rc=0
ESCAPE_MARKER_EXISTS
NONROOT_SAME_UID_RCE
```

Socket, App Server process와 outside marker의 owner는 모두 `1000:1000`이었다.

## 증거 보존 제한

원본 VM image와 전체 log는 이 bundle에 포함하지 않았다. 첨부 runner/client는 같은 세 가지
오라클(restricted connect 차단, direct write 차단, App Server marker 생성)을 재생성한다. Host가
unprivileged user namespace를 막으면 sandbox command가 실행되기 전에 실패할 수 있다.

## 0.148.0 local client sanity check

2026-08-21에 첨부 `poc_uds_client.py`를 `codex-cli 0.148.0` Unix listener에 sandbox 밖에서
직접 연결해 protocol compatibility를 검사했다. `initialize`와 `process/spawn`이 성공했고,
`process/exited(exitCode=0)` 및 `UDS_APP_SERVER_RCE` marker를 확인했다.

같은 host의 full sandbox runner는 restricted control을 시작하기 전에 bubblewrap가
`loopback: Failed RTM_NEWADDR: Operation not permitted`로 종료돼 **INCONCLUSIVE**였다. 따라서
이 결과를 0.148.0 full-network sandbox edge의 성공이나 패치 판정으로 사용하지 않는다.
