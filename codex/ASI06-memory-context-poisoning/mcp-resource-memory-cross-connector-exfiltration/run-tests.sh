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
expected_commit="711a5f8b3a6eb40134146ae9ec22fdcdda5e3170"
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

target_files=(
  codex-rs/core/tests/suite/sqlite_state.rs
  codex-rs/core/src/tools/handlers/mcp_resource.rs
  codex-rs/memories/write/src/startup_tests.rs
)
if ! git -C "$repo_root" diff --quiet -- "${target_files[@]}" ||
   ! git -C "$repo_root" diff --cached --quiet -- "${target_files[@]}"; then
  echo "refusing to touch test targets because they already contain changes" >&2
  exit 1
fi

applied=()
cleanup() {
  local i patch
  for ((i=${#applied[@]}-1; i>=0; i--)); do
    patch="${applied[$i]}"
    if git -C "$repo_root" apply --reverse --check "$patch" >/dev/null 2>&1; then
      git -C "$repo_root" apply --reverse "$patch"
    fi
  done
}
trap cleanup EXIT INT TERM

apply_one() {
  local patch="$1"
  git -C "$repo_root" apply --check "$patch"
  git -C "$repo_root" apply "$patch"
  applied+=("$patch")
}

reverse_all() {
  cleanup
  applied=()
}

cd "$repo_root/codex-rs"

cargo_exec() {
  if command -v rustup >/dev/null 2>&1; then
    rustup run stable cargo "$@"
  else
    cargo "$@"
  fi
}

cargo_exec build -p codex-rmcp-client --bin test_stdio_server

run_test() {
  if command -v rustup >/dev/null 2>&1; then
    RUST_MIN_STACK=8388608 NEXTEST_PROFILE=local \
      rustup run stable cargo nextest run --no-fail-fast "$@"
  else
    RUST_MIN_STACK=8388608 NEXTEST_PROFILE=local \
      cargo nextest run --no-fail-fast "$@"
  fi
}

echo "== live provenance-bypass test =="
apply_one "$here/reproduction-test.patch"
run_test -p codex-core \
  mcp_resource_read_leaves_thread_memory_mode_enabled_when_configured -- --nocapture
reverse_all

echo "== call-time hardening negative control =="
apply_one "$here/hardening-regression-test.patch"
apply_one "$here/proposed-hardening.patch"
run_test -p codex-core \
  mcp_resource_read_marks_thread_memory_mode_polluted_when_configured -- --nocapture
reverse_all

echo "== phase-1 persistence edge =="
apply_one "$here/phase1-persistence-test.patch"
run_test -p codex-memories-write \
  memories_startup_phase1_persists_mcp_resource_output_marker -- --nocapture
reverse_all

echo "== phase-2 consolidation edge =="
apply_one "$here/phase2-consolidation-test.patch"
run_test -p codex-memories-write \
  memories_startup_phase2_can_consolidate_resource_marker_into_summary -- --nocapture
reverse_all

echo "PASS: live primitive, hardening control, phase-1, and phase-2 edge tests completed"
