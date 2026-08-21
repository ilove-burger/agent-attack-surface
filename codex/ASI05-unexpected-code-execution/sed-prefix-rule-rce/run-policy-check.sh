#!/usr/bin/env bash
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
codex_bin="${1:-${CODEX_BIN:-}}"
if [[ -z "$codex_bin" || ! -x "$codex_bin" ]]; then
  echo "usage: $0 /absolute/path/to/codex" >&2
  exit 2
fi

work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT INT TERM
candidate="$work_dir/candidate.json"
negative="$work_dir/negative.json"

"$codex_bin" execpolicy check --pretty \
  --rules "$here/poc/policy.rules" \
  -- sed -n 1,260p /tmp/codex-sed-poc-input.txt \
  -e '1e /usr/bin/id' > "$candidate"

"$codex_bin" execpolicy check --pretty \
  --rules "$here/poc/policy.rules" \
  -- sed -n 1,260p /tmp/codex-sed-different-input.txt \
  -e '1e /usr/bin/id' > "$negative"

python3 - "$candidate" "$negative" <<'PY'
import json
import sys
from pathlib import Path

candidate = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
negative = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
expected = ["sed", "-n", "1,260p", "/tmp/codex-sed-poc-input.txt"]

matches = candidate.get("matchedRules", [])
if candidate.get("decision") != "allow":
    raise SystemExit("FAIL: candidate was not allowed")
if len(matches) != 1:
    raise SystemExit(f"FAIL: expected one candidate rule, got {len(matches)}")
prefix = matches[0].get("prefixRuleMatch", {}).get("matchedPrefix")
if prefix != expected:
    raise SystemExit(f"FAIL: unexpected matched prefix: {prefix!r}")
if negative.get("decision") == "allow" or negative.get("matchedRules"):
    raise SystemExit("FAIL: different-input negative control matched")

print(json.dumps({
    "candidate_decision": candidate.get("decision"),
    "matched_prefix": prefix,
    "appended_argv": ["-e", "1e /usr/bin/id"],
    "different_input_matched": False,
    "verdict": "CONFIRMED",
}, ensure_ascii=False, indent=2))
PY

echo
"$codex_bin" --version
sha256sum "$codex_bin"

