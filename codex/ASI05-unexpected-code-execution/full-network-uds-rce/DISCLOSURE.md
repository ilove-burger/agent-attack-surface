# Codex full-network UDS RCE

> 상태: `소스 확인` · `Docker network 행렬` · `Ubuntu VM UID 1000 전체 체인` · `벤더 미확인 0-day 후보`
>
> 증거 표기: **[소스]** 구현에서 확인 · **[동적]** 로컬/VM 실행 관찰 · **[추론]** 확인된 edge에서 도출 · **[미검증]** 별도 검증 필요
>
> 연구자 소유 socket과 marker만 사용한 비공개 제출용 초안.


## 핵심 요약

- Codex CLI `0.147.0`의 Linux workspace 제한 sandbox는 direct full-network가 허용되고 managed network proxy가 꺼져 있으면 network seccomp를 설치하지 않아 AF_UNIX 연결도 제한하지 않는다.
- 같은 사용자로 실행 중인 Codex App Server Unix listener가 있으면 sandboxed process가 control socket에 인증 없이 WebSocket으로 접속하고 `fs/writeFile` 또는 `process/spawn`을 호출해 파일시스템 sandbox를 우회할 수 있다.
- Ubuntu 커널 VM의 UID 1000 일반 사용자 재현에서 직접 host-side marker 쓰기는 `Read-only file system`으로 차단됐지만 App Server `process/spawn` 경유 쓰기는 성공했으며 소켓·서버·marker가 모두 UID/GID 1000이었다.
- restricted network와 managed proxy 활성화 조건에서는 소켓 연결이 `EPERM`으로 차단됐으므로 root cause는 full-network가 인터넷 접근뿐 아니라 로컬 IPC 격리까지 함께 제거하는 정책 결합에 있다.
- 기존 ancestor relocation·CVE-2025-59532·CVE-2025-61260과 root cause 및 진입점이 겹치지 않는 별도 ASI05 후보이며, App Server listener와 full-network가 동시에 필요하므로 현재 잠정 심각도는 High다.

## 배경과 목적

Codex의 workspace sandbox는 모델 또는 workspace의 코드를 실행하되 사용자 홈과 workspace 밖 파일을 보호하는 경계다. 네트워크 허용은 일반적으로 외부 서비스 접근을 위한 별도 권한으로 이해되지만, Linux의 direct full-network 구현은 인터넷 소켓만 여는 것이 아니라 network seccomp 자체를 생략한다. 이 보고서는 그 결과 sandbox가 같은 UID의 로컬 Unix domain socket에 접근하고, 더 높은 파일·프로세스 권한을 가진 Codex App Server를 confused deputy로 사용할 수 있는지 검증한다.

분석 대상은 다음과 같다.

| 항목 | 값 |
|---|---|
| 제품 | OpenAI Codex CLI |
| 확인 버전 | `codex-cli 0.147.0`, `@openai/codex@0.147.0` |
| 소스 기준 | `be6e8eac029b183056b7e4402879f15d2c85f61b` (`rust-v0.147.0`) |
| 플랫폼 | Linux bubblewrap·Landlock·seccomp sandbox |
| 공격 경계 | workspace sandbox → 동일 UID App Server control socket |
| 직접 결과 | workspace 밖 임의 파일 읽기·쓰기 및 App Server 권한의 프로세스 실행 |
| 상태 | Docker와 일반 사용자 VM 전체 체인 재현, 벤더 확인 전 0-day 후보 |

## 조사 결과

### 1. full-network에서 network seccomp가 생략된다

Linux sandbox는 `NetworkSandboxPolicy`와 managed proxy 사용 여부로 network seccomp 설치 여부를 결정한다.

```rust
fn should_install_network_seccomp(
    network_sandbox_policy: NetworkSandboxPolicy,
    allow_network_for_proxy: bool,
) -> bool {
    !network_sandbox_policy.is_enabled() || allow_network_for_proxy
}
```

direct full-network에서는 `network_sandbox_policy.is_enabled() == true`이고 proxy를 사용하지 않으므로 반환값은 `false`다. 이어지는 `network_seccomp_mode`는 `None`을 반환하며 AF_INET뿐 아니라 AF_UNIX에 대한 syscall 필터도 설치하지 않는다.

관련 구현:

- `codex-rs/linux-sandbox/src/landlock.rs:96-116`: seccomp 설치 여부와 모드 결정
- `codex-rs/features/src/lib.rs:1089-1098`: `network_proxy`는 experimental이며 기본값 `false`

이 동작은 “인터넷을 허용한다”와 “호스트의 로컬 IPC endpoint에 접근한다”를 같은 네트워크 허용 상태로 합친다. Landlock 파일 규칙은 Unix socket에 대한 `connect(2)` 권한 경계를 대신하지 못하므로, socket 경로가 workspace 밖에 있어도 연결이 성립한다.

### 2. App Server Unix listener에는 연결자 인증이 없다

App Server control socket의 기본 위치는 다음과 같다.

```text
$CODEX_HOME/app-server-control/app-server-control.sock
```

listener는 socket을 bind하고 mode를 `0600`으로 바꾼 뒤 연결을 accept하여 WebSocket handshake를 수행한다. TCP listener에 별도로 존재하는 인증과 달리 이 Unix listener 경로에는 peer credential, sandbox ancestry, nonce 또는 capability token 검사가 없다.

`0600`은 다른 Unix 계정을 차단하지만 sandbox와 App Server가 같은 UID로 동작하는 일반적인 배치에서는 보안 경계가 되지 않는다. 실제 일반 사용자 테스트에서도 socket owner와 공격 process가 모두 UID 1000이어서 정상적으로 연결됐다.

App Server는 `codex app-server --listen unix://`로 명시적으로 시작할 수 있으며 remote-control daemon 흐름에서도 control socket을 사용한다. 따라서 listener가 항상 실행되는 기본 TUI만의 문제라고 표현해서는 안 되지만, listener가 실행 중인 환경에서는 socket mode만으로 sandboxed descendant를 구분할 수 없다.

관련 구현:

- `codex-rs/app-server-transport/src/transport/unix_socket.rs:20-88`: `0600`, accept, WebSocket upgrade
- `codex-rs/app-server-daemon/src/backend/pid.rs:413-421`: Unix App Server 시작 명령
- `codex-rs/app-server-daemon/src/lib.rs:494` 이후: daemon 보장·시작 흐름

### 3. control socket은 sandbox 밖 filesystem과 process sink를 제공한다

App Server의 `fs/readFile`과 `fs/writeFile`은 environment filesystem을 `sandbox: None`으로 호출한다. 이 API는 experimental capability를 요구하지 않는다.

```rust
self.file_system()?
    .write_file(&path, bytes, /*sandbox*/ None)
    .await?;
```

`process/spawn`은 요청의 argv와 절대 cwd를 받아 App Server의 environment를 상속한 child process를 시작한다. 별도의 Codex command sandbox를 적용하는 코드가 없다.

`process/spawn`은 experimental API로 표시되어 있지만 이것은 인증이 아니다. 연결자는 `initialize` 요청에 다음 capability를 선언하기만 하면 된다.

```json
{
  "capabilities": {
    "experimentalApi": true
  }
}
```

initialize processor는 클라이언트가 보낸 값을 connection session에 그대로 저장하고 이후 dispatch가 그 boolean만 검사한다. 실제 PoC는 임의의 client name으로 initialize한 뒤 `process/spawn`을 성공시켰다.

관련 구현:

- `codex-rs/app-server/src/request_processors/fs_processor.rs:64-93`: `sandbox: None` 파일 읽기·쓰기
- `codex-rs/app-server/src/request_processors/process_exec_processor.rs:68-140`: process 환경 구성과 실행
- `codex-rs/app-server/src/request_processors/initialize_processor.rs:63-99`: client-declared experimental capability 저장
- `codex-rs/app-server/src/message_processor.rs:815-823`: experimental capability boolean 검사
- `codex-rs/app-server/src/message_processor.rs:1453-1456`: `process/spawn` dispatch

### 4. 독립된 공격 체인

```text
Linux workspace-restricted sandbox
  + direct full-network
  + managed network proxy 비활성
    → network seccomp 미설치
    → AF_UNIX connect 허용
    → 동일 UID App Server control socket WebSocket 연결
    → initialize에서 experimentalApi=true 자체 선언
    → process/spawn 또는 fs/writeFile 요청
    → App Server 권한으로 workspace 밖 명령 실행·파일 접근
```

이 체인에는 project-local `.codex/config.toml` 변조, ancestor rename, MCP configuration reload 또는 Git helper가 필요하지 않다. 따라서 기존에 확인한 path relocation 계열과 독립적이다.

## 동적 검증

### 조건 행렬

실제 `@openai/codex@0.147.0` 바이너리와 App Server를 사용해 다음 결과를 확인했다.

| sandbox 조건 | AF_UNIX 연결 | workspace 밖 marker | 판정 |
|---|---:|---:|---|
| 일반 `:workspace` | `EPERM` | 생성 안 됨 | 정상 차단 |
| full-network, proxy 꺼짐 | 성공 | 생성됨 | 탈출 성공 |
| full-network, 명시적 socket deny, proxy 꺼짐 | 성공 | 생성됨 | proxy 미사용 시 deny 비적용 |
| full-network, managed proxy 켜짐 | `EPERM` | 생성 안 됨 | 방어 성공 |

명시적인 Unix socket deny는 managed proxy 정책의 일부이므로 proxy 기능 자체가 꺼진 상태에서는 enforcement 경로가 만들어지지 않는다. 이 관찰은 deny parser의 단독 결함이라기보다 direct full-network가 network seccomp를 생략하는 결과로 해석해야 한다.

### UID 1000 일반 사용자 전체 체인

호스트의 AppArmor가 일반 사용자 user namespace 생성을 막는 영향을 제거하기 위해, Ubuntu `7.0.0-28-generic` 커널을 사용한 격리 VM에서 확인했다. root shell은 VM 준비에만 사용하고 실제 App Server와 Codex sandbox는 사용자 `node`, UID/GID 1000으로 실행했다.

먼저 일반 사용자 namespace가 동작하는지 확인했다.

```text
uid=1000(node) gid=1000(node)
uid=0(root) gid=0(root)   # unshare -Ur 내부 표시
unshare_rc=0
```

동일 full-network profile에서 직접 marker 쓰기는 거부됐다.

```text
/bin/sh: can't create /home/node/host-marker: Read-only file system
sandbox_rc=1
BASELINE_DENIED
```

그 다음 같은 sandbox 안의 Node client가 App Server control socket에 연결해 `process/spawn`을 요청했다.

```json
{"id":1,"result":{"userAgent":"nonroot-poc/0.147.0 ...","codexHome":"/home/node/.codex","platformOs":"linux"}}
{"id":2,"result":{}}
{"method":"process/exited","params":{"processHandle":"poc","exitCode":0}}
```

최종 결과:

```text
client_rc=0
ESCAPE_MARKER_EXISTS
NONROOT_SAME_UID_RCE
```

소유권도 다음과 같이 확인했다.

```text
srw------- 1 1000 1000 ... /home/node/.codex/app-server-control/app-server-control.sock
-rw-r--r-- 1 1000 1000 ... /home/node/host-marker
252 ... node node ... codex app-server --listen unix://
260 ... node node ... codex app-server --listen unix://
```

따라서 Docker root, setuid helper 또는 서로 다른 사용자 간 권한 문제가 아니라 **동일한 비특권 UID 안에서 sandboxed child와 unsandboxed service를 구분하지 못하는 문제**다.

## 분석

### 기존 후보 및 1-day와의 중복성

| 항목 | 진입점 | root cause | 실행 sink | 이번 후보와 관계 |
|---|---|---|---|---|
| ancestor relocation MCP RCE | writable ancestor rename | 호출별 path 기반 metadata 보호 재해석 | 새 세션의 stdio MCP startup | 영향은 유사하지만 독립 체인 |
| CVE-2025-59532 | 모델 생성 `cwd` | workspace root 경계 확장 | sandbox 밖 파일 쓰기·실행 | 일반적 sandbox escape 선행 사례 |
| CVE-2025-61260 | repository `.env`와 `CODEX_HOME` | project config를 전역 신뢰 설정으로 오인 | stdio MCP startup | 설정 신뢰 문제로 진입점이 다름 |
| 이번 후보 | direct full-network + App Server UDS | network 허용이 로컬 IPC 격리까지 제거 | App Server `fs/*`, `process/spawn` | 별도 root cause·별도 endpoint |

최종 영향이 모두 Codex 권한의 파일 접근 또는 명령 실행이라는 점만으로 같은 취약점으로 합치면 안 된다. 패치 위치도 각각 path identity, config trust, network seccomp·IPC authentication으로 다르다.

### OWASP Agentic Top 10 분류

#### 주 분류 — ASI05 Unexpected Code Execution

workspace sandbox 내부에서 직접 실행하면 차단되는 명령을 App Server가 sandbox 없이 실행한다. 최종 보안 결과가 예상하지 않은 host-side code execution이므로 ASI05가 주 분류다.

#### 보조 분류 — ASI02 Tool Misuse & Exploitation

full-network와 App Server API는 각각 정상 기능이지만 조합되면 filesystem sandbox를 우회하는 deputy가 된다. 권한마다 개별 의미만 고려하고 조합 후 권한 상한을 유지하지 못한다는 점에서 ASI02가 관련된다.

#### 조건부 분류 — ASI03 Identity & Privilege Abuse

socket mode `0600`은 “같은 UID이면 같은 신뢰 수준”이라는 OS identity를 사용한다. 그러나 같은 UID 안에서도 sandboxed child와 App Server는 서로 다른 권한 수준을 가져야 한다. 이 confused-deputy 성격 때문에 ASI03도 조건부로 적용할 수 있다.

### 잠정 CWE 매핑

- **CWE-284 Improper Access Control:** App Server가 sandboxed peer를 식별하거나 privileged method를 제한하지 않는다.
- **CWE-441 Unintended Proxy or Intermediary:** 제한된 process가 App Server를 intermediary로 사용해 원래 접근할 수 없는 파일과 프로세스 권한을 행사한다.
- **CWE-749 Exposed Dangerous Method or Function:** local control socket이 `fs/writeFile`과 `process/spawn` 같은 고권한 기능을 인증 없이 노출한다.
- **CWE-653 Improper Isolation or Compartmentalization:** direct network 허용이 인터넷 접근과 host-local IPC 격리를 분리하지 않는다.

CWE 선택은 벤더 triage 전 잠정 매핑이다. root cause를 하나로 축약하면 “network capability가 local privileged IPC capability로 확대되고, IPC server도 peer의 sandbox 수준을 구별하지 않는다”이다.

### 공격 전제조건과 제한

- Linux에서 재현됐다. macOS Seatbelt는 AF_UNIX와 일반 outbound rule 구성이 달라 현재 결과를 그대로 일반화할 수 없다.
- filesystem policy는 workspace 제한 상태여야 sandbox escape 의미가 있다.
- direct full-network가 활성화되어야 한다. 기본 restricted profile에서 소켓 연결은 차단됐다.
- `network_proxy`가 비활성화되어야 한다. 확인 버전에서는 기본값이 `false`지만 기능·정책 배치에 따라 달라질 수 있다.
- 동일 UID의 App Server Unix listener 또는 remote-control daemon이 실행 중이어야 한다. 기본 TUI만 실행한 모든 환경이 자동으로 취약하다고 단정하지 않는다.
- `process/spawn`에는 client-declared experimental capability가 필요하지만 `fs/writeFile`에는 필요하지 않다.
- 이 PoC는 Codex command sandbox escape이며 VM·Docker·OS 사용자 계정 경계를 벗어나는 공격이 아니다.

### 심각도 판단

성공하면 Codex/App Server가 접근할 수 있는 홈 디렉터리, 소스 코드, SSH·cloud credential, 사용자 프로세스 환경으로 영향이 확대될 수 있다. command execution primitive가 실제 일반 사용자 환경에서 확인됐으므로 영향 상한은 높다.

반면 full-network와 실행 중인 App Server listener가 모두 필요하며, typical restricted sandbox에서는 차단된다. 따라서 현재 잠정 판정은 **High, 조건부**다. listener의 실제 기본 노출 빈도와 remote-control 사용률을 확인하기 전에는 CVSS 수치를 확정하지 않는다.

### 추가 영향 가설

동일한 seccomp 생략은 App Server뿐 아니라 `SSH_AUTH_SOCK`, GPG agent, Podman·Docker socket, systemd user bus, IDE control socket 같은 동일 UID의 Unix endpoint에도 영향을 줄 수 있다. 다만 이 보고서에서 end-to-end로 검증한 endpoint는 Codex App Server뿐이므로 다른 서비스의 실질 영향은 별도 후보로 검증해야 한다.

## 권고 사항

### sandbox 측

1. full internet network를 허용해도 AF_UNIX는 기본 차단하고, 필요한 socket만 정확한 경로·identity로 allowlist한다.
2. network seccomp를 전부 생략하지 말고 AF_INET·AF_INET6 정책과 AF_UNIX 정책을 독립적으로 구성한다.
3. `network_proxy`가 꺼져 있어도 Unix socket deny 규칙은 fail closed로 적용하거나, 적용할 수 없는 구성을 시작 전에 거부한다.
4. `SSH_AUTH_SOCK`, container runtime socket, user bus 등 고권한 endpoint에 대한 기본 deny 회귀 테스트를 추가한다.

### App Server 측

1. control socket 연결 시 `SO_PEERCRED`만 확인하는 데 그치지 말고, 시작 시 발급한 unguessable capability token 또는 상호 인증 handshake를 요구한다.
2. `process/spawn`, `fs/writeFile`, config mutation 등 고권한 method는 별도의 권한 scope와 사용자 승인을 요구한다.
3. `experimentalApi: true`를 클라이언트가 자체 선언하는 기능 협상과 privileged authorization을 분리한다.
4. 가능하면 control socket server 자체를 최소 권한 sandbox 안에서 실행하고 파일·프로세스 API에 명시적인 root policy를 적용한다.
5. sandboxed Codex descendant의 peer PID·cgroup·namespace를 식별할 수 있다면 privileged control connection을 거부한다. 단, PID 계층 검사만을 유일한 인증으로 사용해서는 안 된다.

### 회귀 테스트

- workspace-restricted + network enabled + proxy disabled에서 App Server socket 연결이 거부되는지 확인한다.
- restricted, direct full-network, proxy-routed network 각각에 대해 AF_INET·AF_INET6·AF_UNIX 행렬을 테스트한다.
- UID가 같아도 sandboxed child가 `fs/writeFile`과 `process/spawn`을 호출하지 못하는지 검증한다.
- client-declared `experimentalApi`가 authorization을 부여하지 않는지 확인한다.
- listener가 재시작되거나 socket path가 교체돼도 token·peer binding이 유지되는지 검사한다.

## 출처

- [Codex Linux network seccomp 설치 결정](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/linux-sandbox/src/landlock.rs#L96-L116)
- [Codex network proxy 기본 비활성 설정](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/features/src/lib.rs#L1089-L1098)
- [App Server Unix control socket acceptor](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/app-server-transport/src/transport/unix_socket.rs#L20-L88)
- [App Server filesystem API의 sandbox 없는 접근](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/app-server/src/request_processors/fs_processor.rs#L64-L93)
- [App Server `process/spawn` 실행 경로](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/app-server/src/request_processors/process_exec_processor.rs#L68-L140)
- [App Server client capability 초기화](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/app-server/src/request_processors/initialize_processor.rs#L63-L99)
- 로컬 동적 검증: `@openai/codex@0.147.0` Docker 조건 행렬 및 Ubuntu kernel VM UID 1000 전체 체인

## 관련 노트

- [ancestor relocation MCP RCE](../ancestor-relocation-mcp-rce/) — 같은 버전에서 command sandbox 밖 실행으로 이어지지만 path relocation과 project config 변조를 사용하는 독립 후보다.
