# Sanitized observed results

> 실행일: 2026-08-19
> source: `85fc4def358b7df21883e72ae8dda43a0f572f32`
> 인증: fixture user/account IDs
> backend: loopback mock
> 판정: **6/6 PASS**

2026-08-21에 이 bundle의 `run-proof.sh`로 같은 고정 commit에서 다시 실행했으며 2/2, 1/1,
3/3이 모두 통과했다. Runner 종료 후 네 개의 patch target에 staged/unstaged 변경이 남지 않았음을
확인했다.

## Scoped tests

```text
PASS codex-cloud-config cache::tests::validation_proof_cache_save_follows_symlink_and_clobbers_target
PASS codex-cloud-config service::tests::validation_proof_public_hmac_enables_persistent_unapproved_full_host_access
Summary: 2 tests run, 2 passed

PASS codex-protocol permissions::tests::validation_proof_workspace_write_allows_custom_named_codex_home_cache
Summary: 1 test run, 1 passed

PASS codex-core::all suite::cli_stream::validation_proof_cli_cloud_cache_save_follows_symlink
PASS codex-core::all suite::cli_stream::validation_proof_cli_public_hmac_cache_enables_unapproved_host_write
PASS codex-core::all suite::cli_stream::validation_proof_cli_restricted_writer_to_forged_cache_to_host_write_full_chain
Summary: 3 tests run, 3 passed
```

## Two-process oracle

```text
process 1 effective sandbox: workspace-write [workdir]
process 1 custom CODEX_HOME cache generation: success
process 1 outside marker: Permission denied

process 2 effective approval: never
process 2 effective sandbox: danger-full-access
process 2 outside marker: observed
startup backend requests before cache use: 0
```

## Symlink writer oracle

정상 backend fetch 뒤 cache save가 cache-path symlink의 outside target을 cache JSON으로 교체했다.
경로 선택은 공격자가 통제하지만 내용은 fixed-format cache JSON이다. arbitrary-content write로
분류하지 않는다.

## 안전성과 한계

- 실제 `auth.json`, token 또는 OpenAI backend를 사용하지 않았다.
- 모든 파일은 test `TempDir` 아래에 생성됐다.
- 이 host의 actual restricted writer는 legacy Landlock를 사용했다. newer bubblewrap runtime에 일반화하지 않는다.
- writable custom-named `CODEX_HOME`과 다음 process의 local sandbox override 부재가 필요하다.
