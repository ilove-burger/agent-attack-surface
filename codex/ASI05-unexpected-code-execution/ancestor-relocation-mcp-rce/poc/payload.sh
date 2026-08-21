#!/bin/sh

{
    printf '%s\n' 'CODEX_MCP_HOST_RCE'
    printf 'uid: '
    id
    printf 'pid: %s\n' "$$"
    printf 'ppid: %s\n' "$PPID"
    printf 'cwd: '
    pwd
    printf 'parent_cmdline: '
    tr '\000' ' ' < "/proc/$PPID/cmdline"
    printf '\n'
} > /root/codex-mcp-host-rce
exit 1
