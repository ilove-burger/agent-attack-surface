#!/bin/sh
set -eu

image_name="codex-ancestor-relocation-mcp:0.147.0"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
trials=${TRIALS:-1}

case "$trials" in
    ''|*[!0-9]*|0)
        printf '%s\n' 'TRIALS must be a positive integer' >&2
        exit 2
        ;;
esac

docker build --tag "$image_name" "$script_dir"

trial=1
while [ "$trial" -le "$trials" ]
do
    printf '\n=== fresh container trial %s/%s ===\n' "$trial" "$trials"
    docker run --rm --privileged "$image_name"
    trial=$((trial + 1))
done

printf '\nAll %s fresh-container trial(s) passed.\n' "$trials"
