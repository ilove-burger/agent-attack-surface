#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
    echo "ERROR: this runner must execute on macOS (Darwin)" >&2
    exit 2
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 /absolute/path/to/codex [run-root]" >&2
    exit 2
fi

codex_bin=$1
run_root=${2:-/tmp/codex-execpolicy-macos-0.149.1}
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
driver="$script_dir/poc-tui-execpolicy-substitution.py"

if [ ! -x "$codex_bin" ]; then
    echo "ERROR: Codex binary is missing or not executable: $codex_bin" >&2
    exit 2
fi

case "$(uname -m)" in
    arm64)
        expected_sha256=f0d8762236594359b60cfbe17f4c7e945a3ce8d1c91e74778838c968d250fb6c
        ;;
    x86_64)
        expected_sha256=19ad079130409e2d32cbb4b02b3d622ab44e7de93a2898ce58908a0f2f5d7a06
        ;;
    *)
        echo "ERROR: unsupported macOS architecture: $(uname -m)" >&2
        exit 2
        ;;
esac

actual_sha256=$(shasum -a 256 "$codex_bin" | awk '{print $1}')
if [ "$actual_sha256" != "$expected_sha256" ]; then
    echo "ERROR: Codex binary SHA-256 mismatch" >&2
    echo "expected: $expected_sha256" >&2
    echo "actual:   $actual_sha256" >&2
    exit 2
fi

python3 -c 'import pexpect' 2>/dev/null || {
    echo "ERROR: Python package pexpect is required (python3 -m pip install --user pexpect)" >&2
    exit 2
}

python3 "$driver" \
    --codex "$codex_bin" \
    --run-dir "$run_root/positive" \
    --scenario execpolicy-prefix-model-chain \
    --mutation-transport model-apply-patch

python3 "$driver" \
    --codex "$codex_bin" \
    --run-dir "$run_root/approve-once-control" \
    --scenario approve-once-control \
    --mutation-transport model-apply-patch

python3 "$driver" \
    --codex "$codex_bin" \
    --run-dir "$run_root/argv-change-control" \
    --scenario argv-change-control \
    --mutation-transport model-apply-patch

python3 - "$run_root" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
for name in ("positive", "approve-once-control", "argv-change-control"):
    result = json.loads((root / name / "result.json").read_text(encoding="utf-8"))
    print(
        f"{name}: pass={result['pass']} "
        f"classification={result['classification']} "
        f"prompts={result['command_approval_prompts']} "
        f"marker={result['marker_observed']}"
    )
PY
