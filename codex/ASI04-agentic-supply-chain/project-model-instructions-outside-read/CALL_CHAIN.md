# Config → base_instructions → Responses `instructions` call chain

> 대상: `codex-cli 0.149.0` (real binary SHA-256 `bbc3341e44c9ead340ed9570c17be936e37870f570751a941699ffd04d672827`)
> 소스: `https://github.com/openai/codex.git`, `rust-v0.148.0` 체크아웃(`/home/mjhy3/agent/codex-src`)
>       — 0.149.0과 해당 코드 경로에 동작 차이 없음(런타임 검증으로 재확인, 아래).
> 검증 방식: **[소스]** 함수/라인 직접 확인 · **[런타임]** `hunt-shell` 안에서 `strace`로 실제 syscall 관찰

이 문서는 `README.md`/`analysis.json`이 정리한 4개 root-cause 지점을, 실제 소스 파일:라인과
런타임에서 관찰한 syscall로 이어 붙인다. 목적은 "소스를 읽고 추정했다"가 아니라 "그 추정대로
프로세스가 실제로 동작했다"를 독립적으로 증명하는 것이다.

## 전체 체인

```
project .codex/config.toml (trust 후 병합)
  → model_instructions_file 경로를 .codex/ 기준 절대경로로 변환 (containment 검사 없음)
    → try_read_non_empty_file() 이 그 절대경로를 open()+read()
      → Config.base_instructions: Option<String>
        → SessionConfiguration.base_instructions: String
          → Session::get_base_instructions() → BaseInstructions{text, provenance}
            → Prompt.base_instructions (턴 빌드 시 주입)
              → build_responses_request() 가 prompt.base_instructions.text 를 instructions 필드로 사용
                → ResponsesApiRequest.instructions → HTTP 요청 바디로 전송
```

## 단계별 근거

### 1. Project config 병합 — **[소스]**

`codex-rs/config/src/loader/mod.rs:1346` `async fn load_project_layers(...)`.
프로젝트 루트에서 `.codex/config.toml`을 읽어 config layer stack에 추가한다. 이 호출 자체는
`trusted_project_root()` 게이트(commit `7351c129`, `rust-v0.88.0-alpha.9`+) 뒤에서만 실행되므로,
공격 전제는 "사용자가 이 프로젝트를 신뢰함"이다.

### 2. 경로 절대화, containment 검사 없음 — **[소스]**

`codex-rs/config/src/loader/mod.rs:1218` `resolve_relative_paths_in_config_toml()`이 TOML을
`ConfigToml`로 역직렬화하면서 `AbsolutePathBufGuard`의 base를 해당 `.codex/` 디렉터리로 설정한다.
실제 절대화는 `codex-rs/utils/absolute-path/src/lib.rs:47`
`AbsolutePathBuf::resolve_path_against_base()`가 수행하는데, 결과 경로가 프로젝트/repository
내부에 머무르는지는 검사하지 않는다. 따라서 `model_instructions_file = "../../outside/x"`,
절대경로, symlink 전부 유효한 값이 된다.

### 3. 해석된 경로를 실제로 읽음 — **[소스 + 런타임]**

**[소스]** `codex-rs/core/src/config/mod.rs:3774-3786`:

```rust
let model_instructions_path = cfg.model_instructions_file.as_ref();
let file_base_instructions = Self::try_read_non_empty_file(
    fs, model_instructions_path, "model instructions file",
).await?;
let base_instructions = base_instructions.or(file_base_instructions).or(cfg.instructions.clone());
```

`try_read_non_empty_file()` 정의는 `:4210`, 내부적으로 `fs.read_file_text(&path_uri, /*sandbox*/ None)`
를 호출한다.

**[런타임]** `hunt-shell` 안에서 실제 codex 바이너리를 `strace -f -e trace=open,openat,openat2,read`로
감싸 동일한 E2E(트리거는 `model-instructions-ui-trust-e2e.py`, fresh clone + 실제 startup trust UI
승인, bypass 없음)를 재실행했다. 결과 로그에서 project 밖 절대경로가 **`open()`(legacy syscall,
`openat`이 아님 — 이전 트레이스 필터에 안 걸렸던 이유)** 으로 직접 열리고, 곧바로 canary 내용이
`read()`되는 것을 확인했다:

```text
86  open("/home/mjhy3/hunt/work/codex-model-instructions-strace-run2/e2e/outside/fake-secret.txt",
        O_RDONLY|O_NONBLOCK|O_LARGEFILE|O_CLOEXEC) = 41
86  read(41, "HUNMA_UI_TRUST_OUTSIDE_MODEL_INSTRUCTIONS_0_149_0_ONLY\n", 55) = 55
```

같은 스레드(tid 86)에서 동일 패턴이 이 실행 동안 총 7회 관찰됐다(설정 재로딩·미리보기 경로와 일치).
경로는 project 디렉터리(`e2e/project/`)가 아니라 **형제 디렉터리**(`e2e/outside/`)를 가리키는
완전히 resolve된 절대경로다 — 소스에서 예측한 "containment 없는 절대화"가 그대로 실증됐다.

### 4~6. Config → Session → Prompt 전달 — **[소스]**

- `Config.base_instructions: Option<String>` 필드: `core/src/config/mod.rs:626`
- `Session` 생성 시 전달: `core/src/session/session.rs:624` (`config.base_instructions.is_some()` 분기)
- `SessionConfiguration.base_instructions: String`: `core/src/session/session.rs:84`
- 조회 헬퍼: `core/src/session/mod.rs:1286` `Session::get_base_instructions()` →
  `BaseInstructions{text, provenance}`
- 턴 빌드 시 실제 사용: `core/src/session/turn.rs:1333`
  (`let base_instructions = sess.get_base_instructions().await;`) — compaction 경로
  (`compact.rs:279`)뿐 아니라 **일반 턴**에서도 동일 헬퍼를 사용함을 확인했다.

### 7. Responses 요청의 `instructions` 필드로 직렬화 — **[소스 + 런타임]**

**[소스]** `codex-rs/core/src/client.rs:844-896` `build_responses_request()`:

```rust
let (instructions, tools) = if model_info.use_responses_lite {
    // ... base_instructions.text 를 developer 메시지로 prefix
} else {
    (prompt.base_instructions.text.clone(), Some(...))   // <- 여기
};
```

이 `instructions`는 `ResponsesApiRequest.instructions`가 되고, `core/src/client.rs:587-603`에서
구조 분해되어 실제 요청 payload로 나간다.

**[런타임]** loopback mock 서버가 캡처한 `request-001.json`의 `instructions` 필드가 canary 문자열과
정확히 일치함을 3회 독립 실행(v2/v3/v4, 전부 `hunt-shell`, fresh dir)에서 확인했다(아래 표).
`instructions_length: 54`가 매 실행 동일했다.

## 런타임 3-way 증거 요약

| Run | 방식 | 확인한 것 |
|---|---|---|
| v2/v3/v4 (UI E2E, 각 1회) | 실제 startup TUI에 Enter로 승인 → loopback 요청 캡처 | 캡처된 `instructions` == canary, 3/3 PASS |
| strace-run2 (UI E2E + strace) | 동일 E2E를 `open/openat/openat2/read` 트레이스 하에 재실행 | project 밖 절대경로 `open()` + 정확한 canary bytes `read()` — 소스 3단계가 실제로 실행됨을 syscall 레벨에서 확인 |

세 증거(소스 코드, 프로세스 syscall, 네트워크로 나간 요청 바디)가 서로 독립적으로 같은 결론을
가리킨다: containment 없는 절대경로가 실제로 열리고, 그 내용이 그대로 모델 요청의 system-level
instructions로 전송된다.

## 증거 파일

- 소스 체크아웃: `/home/mjhy3/agent/codex-src` (`rust-v0.148.0`)
- UI E2E 드라이버: `/home/mjhy3/agent/hunting-box/model-instructions-ui-trust-e2e.py`
- 안정성 3/3:
  - v2 result.json SHA-256 `16d91670b33fb818152c0e8eb06152b7f1271f621804acc7f2a6011141788032`
    (`/home/mjhy3/agent/hunting-box/work/codex-model-instructions-ui-trust-0.149.0-v2/result.json`)
  - v3 result.json SHA-256 `6617b4be9b2aa48423226b55d631032a9958769e639104f69c6eeaf2c43eace2`
    (`/home/mjhy3/agent/hunting-box/work/codex-model-instructions-ui-trust-0.149.0-v3/result.json`)
  - v4 result.json SHA-256 `9fc7ee0482ba17caf7cb35f379fb16198dd3699186a648a3d3f87022d76873b9`
    (`/home/mjhy3/agent/hunting-box/work/codex-model-instructions-ui-trust-0.149.0-v4/result.json`)
- strace 원본 로그 SHA-256 `eb129a89f62ec3c7f72f4c6749776ea8be2d360aff04e3932b05635ea497f8d1`
  (`/home/mjhy3/agent/hunting-box/work/codex-model-instructions-strace-run2/strace.log`, 12,851줄)
- strace 실행의 result.json SHA-256 `c294348e029d3d112c6c4be212aa5085c19d41bfe51c9ea2c18d73e0e8a469ae`
  (`/home/mjhy3/agent/hunting-box/work/codex-model-instructions-strace-run2/e2e/result.json`, `pass: true`)
- strace 실행용 wrapper: `/home/mjhy3/agent/hunting-box/work/strace-codex-wrapper.sh`
  (SHA-256 `182b130a9129b6fd1e8f871c4e3818795affaa5804cd2bf81d328cfda4abaccd`)

> **주의:** strace 실행의 `result.json`에 기록된 `codex_sha256`은 이 wrapper 스크립트 자체의
> 해시다 — 드라이버가 `--codex` 인자로 받은 파일을 그대로 해싱하기 때문. 실제로 실행된 codex
> 바이너리는 여전히 `bbc3341e44c9ead340ed9570c17be936e37870f570751a941699ffd04d672827`이며(위
> wrapper 스크립트가 이 경로를 하드코딩해서 `exec`), v2/v3/v4의 codex_sha256과 동일함을 별도로
> `sha256sum`으로 재확인했다.

## 재현

```bash
cd /home/mjhy3/agent/hunting-box
./hunt-shell -- bash -c '
  python3 "$HUNT_WORK/model-instructions-ui-trust-e2e.py" \
    --codex "$HUNT_WORK/strace-codex-wrapper.sh" \
    --run-dir "$HUNT_WORK/<fresh-dir>/e2e"
'
# strace-codex-wrapper.sh 는 REAL_CODEX/STRACE_OUT 을 하드코딩하므로 재실행 전 경로를 맞춘다.
grep -n "outside/fake-secret.txt" "$STRACE_OUT" | grep -E "open\(|read\("
```
