#!/bin/sh
set -eu

lab=/tmp/codex-relocation-poc
moved_lab=/tmp/codex-relocation-poc.moved

mv "$lab" "$moved_lab"
mkdir -p "$lab/project"

test -f "$moved_lab/project/.codex/config.toml"
test -d "$lab/project"
