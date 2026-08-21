#!/usr/bin/env bash
set -euo pipefail
export CARGO_INCREMENTAL=0

if command -v rustup >/dev/null 2>&1; then
  export RUSTUP_TOOLCHAIN=stable
  export RUSTC="$(rustup which rustc)"
  export RUSTDOC="$(rustup which rustdoc)"
fi

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="${1:-${CODEX_SOURCE:-}}"
if [[ -z "$repo_root" ]]; then
  echo "usage: $0 /absolute/path/to/openai-codex-checkout" >&2
  exit 2
fi
repo_root="$(cd -- "$repo_root" && pwd -P)"
expected_commit="85fc4def358b7df21883e72ae8dda43a0f572f32"

if [[ ! -d "$repo_root/codex-rs" ]] ||
   ! git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "not an openai/codex source checkout: $repo_root" >&2
  exit 2
fi
actual_commit="$(git -C "$repo_root" rev-parse HEAD)"
if [[ "$actual_commit" != "$expected_commit" ]]; then
  echo "expected source commit $expected_commit, got $actual_commit" >&2
  exit 2
fi

proof_patch="$here/cloud-config-hmac-proof.patch"
cli_patch="$here/actual-cli-e2e.patch"
proof_files=(
  codex-rs/cloud-config/src/cache_tests.rs
  codex-rs/cloud-config/src/service_tests.rs
  codex-rs/protocol/src/permissions.rs
  codex-rs/core/tests/suite/cli_stream.rs
)

if ! git -C "$repo_root" diff --quiet -- "${proof_files[@]}" ||
   ! git -C "$repo_root" diff --cached --quiet -- "${proof_files[@]}"; then
  echo "refusing to touch proof target files because they already contain changes" >&2
  exit 1
fi

git -C "$repo_root" apply --check "$proof_patch"
git -C "$repo_root" apply --check "$cli_patch"
git -C "$repo_root" apply "$proof_patch"
git -C "$repo_root" apply "$cli_patch"

cleanup() {
  if git -C "$repo_root" apply --reverse --check "$cli_patch" >/dev/null 2>&1; then
    git -C "$repo_root" apply --reverse "$cli_patch"
  fi
  if git -C "$repo_root" apply --reverse --check "$proof_patch" >/dev/null 2>&1; then
    git -C "$repo_root" apply --reverse "$proof_patch"
  fi
}
trap cleanup EXIT INT TERM

cd "$repo_root/codex-rs"
run_test() {
  if command -v rustup >/dev/null 2>&1; then
    RUST_MIN_STACK=8388608 NEXTEST_PROFILE=local \
      rustup run stable cargo nextest run --no-fail-fast "$@"
  else
    RUST_MIN_STACK=8388608 NEXTEST_PROFILE=local \
      cargo nextest run --no-fail-fast "$@"
  fi
}

run_test -p codex-cloud-config validation_proof_
run_test -p codex-protocol \
  validation_proof_workspace_write_allows_custom_named_codex_home_cache
run_test -p codex-core --test all 'suite::cli_stream::validation_proof_cli_'
