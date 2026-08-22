# Containment fix + regression test for `model_instructions_file`

> 대상 소스: `codex-src` (`rust-v0.148.0` 체크아웃, `/home/mjhy3/agent/codex-src`)
> 패치: [`proposed-fix.patch`](proposed-fix.patch) · 테스트: [`regression-test.patch`](regression-test.patch)
> 검증: `cargo test -p codex-config` — **패치 없이 실패(재현) / 패치 적용 시 통과**, 전체 스위트
> 261/261 회귀 없음, `cargo check -p codex-core` clean.

## 왜 여기에 붙이나

`resolve_relative_paths_in_config_toml()`(`config/src/loader/mod.rs:1218`)은 `model_instructions_file`
같은 path-like 값을 절대경로로 바꾸기만 하고 containment는 검사하지 않는다. 이 함수는 project
layer뿐 아니라 **user-level(`CODEX_HOME`) layer, managed/cloud config layer**도 공유해서 쓴다
(`core/src/agent/role.rs:151`, `config/src/cloud_config_layers.rs:100`,
`config/src/loader/mod.rs:164,280,450,464,557,1533,1631` 등 총 10곳 이상 호출).

따라서 containment을 이 공용 함수 안에 넣으면 "관리자가 `CODEX_HOME`에 조직 공통
`model_instructions_file`을 프로젝트 밖에 두는" 정당한 사용을 깨뜨린다. 대신 **project layer만
로드하는 `load_project_layers()`**(`config/src/loader/mod.rs:1346`)에서, 그 layer의 `project_root`를
알고 있는 시점에만 containment를 강제한다 — 정책은 "project-sourced 값에만 적용", 범용 경로
해석 로직 자체는 건드리지 않는다.

## 수정 내용

`config/src/loader/mod.rs`의 `load_project_layers()` 루프에 한 단계 삽입:

```rust
let config =
    resolve_relative_paths_in_config_toml(layer.config, layer.dot_codex_folder.as_path())?;
let config = enforce_model_instructions_file_containment(
    config, project_root, &layer.dot_codex_folder, &mut startup_warnings,
);
```

새 함수 `enforce_model_instructions_file_containment()`:
- 절대화된 `model_instructions_file` 값이 `project_root` 아래(`Path::starts_with`)가 아니면
  **해당 키를 제거**(fail-closed — 조용히 신뢰하지 않고, 값을 아예 없앤다)하고 `startup_warnings`에
  경로·이유를 기록한다.
- `project_root` 안이면 손대지 않는다 — 기존 정상 동작 그대로.

## 알려진 한계 (문서에 명시)

이 패치는 **lexical containment**(문자열 경로 비교)이지 canonicalize 기반이 아니다. 프로젝트 안에
`link -> /etc/passwd` 같은 symlink를 두고 `model_instructions_file = "link"`을 지정하면, 절대화된
경로 문자열 자체는 `project_root` 하위([`project_root]/link`)라 이 체크를 통과하지만, 실제 파일시스템
읽기 시점엔 symlink를 따라가 프로젝트 밖 내용을 읽는다.

완전히 막으려면 `try_read_non_empty_file()`(`core/src/config/mod.rs:4210`, 이미 `fs: &dyn
ExecutorFileSystem` 접근 가능)에서 읽기 직전에 `fs.canonicalize()`로 symlink를 해소한 뒤 다시 한번
`project_root` containment를 검사해야 한다. 이번 finding의 실제 PoC(`../../outside/fake-secret.txt`,
`CALL_CHAIN.md` 참고)는 symlink가 아니라 `..` 상대경로였으므로 이 패치로 완전히 막힌다. symlink
변형은 이 패치의 범위 밖으로 남겨두고 한계로 기록한다.

## 회귀 테스트

`config/src/loader/tests.rs`에 두 테스트 추가, 실제 `load_config_layers_state()`(프로덕션 진입점)를
통해 end-to-end로 검증 — mock 없이 실제 config 로딩 파이프라인 전체를 태운다.

1. **`project_model_instructions_file_outside_project_root_is_dropped`**
   `.codex/config.toml`에 `model_instructions_file = "../../outside/secret.md"`를 둔 trusted
   project를 만들고, 로드 후 `effective_config()`에 `model_instructions_file` 키가 **없는지**,
   `startup_warnings()`에 경고가 **있는지** 확인.
2. **`project_model_instructions_file_inside_project_root_is_kept`** (음성 대조군)
   같은 구조에서 `model_instructions_file = "./instructions.md"`(프로젝트 내부)를 두고, 값이
   **정상적으로 해석돼 남아있는지**, 경고가 **없는지** 확인 — 패치가 정상 사용 사례를 깨지 않음을
   증명.

### 패치 유무 대조 (증거)

| 상태 | `outside_project_root_is_dropped` | `inside_project_root_is_kept` |
|---|---|---|
| 패치 **없이** | **FAIL** — `model_instructions_file` = `"/tmp/.tmpYMSNOv/outside/secret.md"`가 그대로 effective config에 남음 (실제 취약점 재현) | PASS (애초에 패치와 무관한 경로) |
| 패치 **적용** | PASS | PASS |

패치 제거 → 실패, 패치 적용 → 통과를 직접 확인했으므로 이 테스트가 실제로 그 결함을 pin하고
있음을 검증했다(단순히 항상 통과하는 테스트가 아님).

### 전체 스위트 / 하위 크레이트

```text
cargo test -p codex-config           → 261 passed; 0 failed
cargo check -p codex-core            → clean (다운스트림 컴파일 영향 없음)
```

## 재현

```bash
cd <openai/codex checkout>/codex-rs   # rust-v0.148.0
git apply <이 폴더>/proposed-fix.patch
git apply <이 폴더>/regression-test.patch
RUSTUP_TOOLCHAIN=stable cargo test -p codex-config project_model_instructions_file -- --nocapture
#   → test result: ok. 2 passed
```
