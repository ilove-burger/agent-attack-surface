# Containment fix + regression test for `model_instructions_file`

> 대상 소스: `codex-src` (`rust-v0.148.0` 체크아웃, `/home/mjhy3/agent/codex-src`)
> 패치: [`proposed-fix.patch`](proposed-fix.patch) · 테스트: [`regression-test.patch`](regression-test.patch)
> 검증: `cargo test -p codex-config` — **각 케이스 패치 없이 실패(재현) / 패치 적용 시 통과**, 전체
> 스위트 263/263 회귀 없음, `cargo check -p codex-core` clean.
> **2026-08-22 갱신:** 최초 patch는 lexical containment만 구현했고 symlink 우회가 한계로 남아있었다.
> 이번 갱신에서 canonicalize 기반 2차 검사를 추가해 그 gap을 닫았다(§"symlink containment 보강").

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
    fs, config, project_root, &layer.dot_codex_folder, &mut startup_warnings,
).await;
```

새 함수 `enforce_model_instructions_file_containment()`는 두 단계로 검사한다:

1. **Lexical pass**: 절대화된 `model_instructions_file` 값이 `project_root` 아래(`Path::starts_with`)가
   아니면 **해당 키를 제거**(fail-closed)하고 `startup_warnings`에 기록한다. `..`와 절대경로 escape를
   문자열 비교만으로 막는다.
2. **Canonicalize pass**: (1)을 통과한 값에 한해, 값과 `project_root`를 각각
   `fs.canonicalize()`(symlink 해소)로 다시 해석하고 그 결과로 containment를 재검사한다. 둘 중 하나라도
   canonicalize에 실패하면(가장 흔한 경우: 파일이 아직 없음) 이 단계는 건너뛰고 lexical 결과를
   유지한다 — 존재하지 않는 파일은 이후 `try_read_non_empty_file()`의 일반 "파일 없음" 에러로
   자연스럽게 처리되며, 이건 보안 판단의 대상이 아니다.

`project_root` 안이면(양쪽 pass 모두) 손대지 않는다 — 기존 정상 동작 그대로.

## symlink containment 보강 (2026-08-22)

최초 patch는 lexical pass만 구현했다. 프로젝트 안에 `link -> /etc/passwd` 같은 symlink를 두고
`model_instructions_file = "link"`을 지정하면, 절대화된 경로 문자열 자체는 `project_root` 하위
(`[project_root]/link`)라 lexical 체크를 통과하지만, 실제 파일시스템 읽기 시점엔 symlink를 따라가
프로젝트 밖 내용을 읽는다 — 이게 gap이었다.

canonicalize pass를 추가해 이 gap을 닫았다. `enforce_model_instructions_file_containment()`가
이제 `fs: &dyn ExecutorFileSystem`를 받아, lexical pass를 통과한 값을 `fs.canonicalize()`로
symlink까지 해소한 뒤 `project_root`도 동일하게 canonicalize해서 재비교한다. 새 헬퍼
`canonicalize_best_effort()`는 canonicalize 실패를 에러로 전파하지 않고 `None`으로 처리한다 —
이 검사는 "존재하는 파일이 symlink로 프로젝트 밖을 가리키는지"만 판단하는 hardening pass이지,
파일 존재 여부에 대한 새로운 하드 실패를 만들지 않기 위함이다.

## 회귀 테스트

`config/src/loader/tests.rs`에 네 테스트, 실제 `load_config_layers_state()`(프로덕션 진입점)를
통해 end-to-end로 검증 — mock 없이 실제 config 로딩 파이프라인 전체를 태운다.

1. **`project_model_instructions_file_outside_project_root_is_dropped`** — `model_instructions_file
   = "../../outside/secret.md"`(lexical escape). 로드 후 `effective_config()`에 키가 **없는지**,
   경고가 **있는지** 확인.
2. **`project_model_instructions_file_inside_project_root_is_kept`** (음성 대조군) —
   `model_instructions_file = "./instructions.md"`(프로젝트 내부). 값이 **정상 보존**되고 경고
   **없는지** 확인.
3. **`project_model_instructions_file_symlink_escape_is_dropped`** — `model_instructions_file =
   "link"`이고 `link`가 프로젝트 밖 파일을 가리키는 symlink. lexical로는 통과하지만 canonicalize
   pass가 잡아서 키가 **없는지**, "symlink" 언급 경고가 **있는지** 확인.
4. **`project_model_instructions_file_symlink_inside_project_root_is_kept`** (음성 대조군) —
   `link`이 프로젝트 **내부** 파일을 가리키는 symlink. 값이 **보존**되고 경고 **없는지** 확인 —
   canonicalize pass가 정당한 symlink 사용까지 막지 않음을 증명.

### 패치 유무 대조 (증거)

| 테스트 | lexical-only 패치 | lexical+canonicalize 패치(최종) |
|---|---|---|
| `outside_project_root_is_dropped` | PASS | PASS |
| `inside_project_root_is_kept` | PASS | PASS |
| `symlink_escape_is_dropped` | **FAIL** — symlink가 그대로 effective config에 남음(gap 재현) | PASS |
| `symlink_inside_project_root_is_kept` | PASS(애초에 gap과 무관) | PASS |

패치 없음(둘 다 미적용) 상태에서는 `outside_project_root_is_dropped`도 함께 FAIL한다(이전 검증,
`§패치 유무 대조` 원본 기록 참고). lexical-only 상태로 되돌려 `symlink_escape_is_dropped`만 별도로
FAIL함을 재확인해, canonicalize pass가 실제로 그 gap을 닫았다는 것과 이 테스트가 그 gap을 정확히
pin하고 있음을 검증했다(단순히 항상 통과하는 테스트가 아님).

### 전체 스위트 / 하위 크레이트

```text
cargo test -p codex-config           → 263 passed; 0 failed
cargo check -p codex-core            → clean (다운스트림 컴파일 영향 없음)
```

## 재현

```bash
cd <openai/codex checkout>/codex-rs   # rust-v0.148.0
git apply <이 폴더>/proposed-fix.patch
git apply <이 폴더>/regression-test.patch
RUSTUP_TOOLCHAIN=stable cargo test -p codex-config project_model_instructions_file -- --nocapture
#   → test result: ok. 4 passed
```
