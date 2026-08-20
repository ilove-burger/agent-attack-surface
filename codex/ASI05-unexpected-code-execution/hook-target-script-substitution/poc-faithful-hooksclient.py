#!/usr/bin/env python3
# codex app-server 를 stdio JSON-RPC(newline-delimited)로 구동해 hooks/list 로
# 프로젝트 hook 의 (key, currentHash) 를 얻는다. 이는 TUI 가 "승인" 시 저장하는 값과 동일하다.
#
#   usage: CODEX_HOME=... poc-faithful-hooksclient.py <codex-binary> <project-abs> <EVENT>
#   stdout: "<key>\t<currentHash>"  (매칭 hook)
#   stderr: 진단 로그
import json, os, subprocess, sys, threading, time

CODEX = sys.argv[1]
PROJ  = sys.argv[2]
EVENT = sys.argv[3] if len(sys.argv) > 3 else "SessionStart"

def log(*a): print("[hooksclient]", *a, file=sys.stderr, flush=True)

proc = subprocess.Popen(
    [CODEX, "app-server"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=PROJ, env=dict(os.environ), text=True, bufsize=1,
)

# app-server stderr 를 흘려보내 hang 방지 + 디버깅
def drain_err():
    for line in proc.stderr:
        log("SRVERR", line.rstrip())
threading.Thread(target=drain_err, daemon=True).start()

def send(obj):
    log("SEND", json.dumps(obj))
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()

def read_response(want_id, timeout=15):
    """id 가 want_id 인 응답이 올 때까지 라인을 읽으며 그 외(알림/이벤트)는 무시."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.02); continue
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log("SKIP(non-json)", line[:120]); continue
        if msg.get("id") == want_id and ("result" in msg or "error" in msg):
            return msg
        log("SKIP", line[:120])
    raise TimeoutError(f"no response for id={want_id}")

# 1) initialize (test 하네스와 동일: camelCase, experimentalApi)
send({"id": 1, "method": "initialize", "params": {
    "clientInfo": {"name": "poc", "title": None, "version": "0.1.0"},
    "capabilities": {"experimentalApi": True},
}})
resp = read_response(1)
if "error" in resp:
    log("initialize ERROR", resp["error"]); sys.exit(2)
log("initialized OK")

# 2) hooks/list (cwds = project). 실패 시 initialized 알림 후 재시도.
def hooks_list(rid):
    send({"id": rid, "method": "hooks/list", "params": {"cwds": [PROJ]}})
    return read_response(rid)

try:
    resp = hooks_list(2)
except TimeoutError:
    log("hooks/list timeout; sending notifications/initialized and retrying")
    send({"method": "notifications/initialized"})
    resp = hooks_list(3)

if "error" in resp:
    log("hooks/list ERROR", resp["error"]); sys.exit(3)

# HooksListResponse{ data:[HooksListEntry{ cwd, hooks:[HookMetadata{key,eventName,currentHash,trustStatus}], warnings, errors }] }
data = (resp.get("result") or {}).get("data") or []
hooks = []
for entry in data:
    for w in entry.get("warnings", []): log("  WARN", w)
    for er in entry.get("errors", []):  log("  ERR", er)
    hooks.extend(entry.get("hooks", []))
log(f"hooks/list -> {len(data)} cwd-entries, {len(hooks)} hooks")
want_snake = {"SessionStart":"session_start","PreToolUse":"pre_tool_use"}.get(EVENT, EVENT.lower())
picked = None
for h in hooks:
    ev = str(h.get("eventName", ""))
    log("  hook", json.dumps({k: h.get(k) for k in ("key","eventName","trustStatus","currentHash")}))
    if ev in (EVENT, want_snake) or want_snake in ev.lower():
        picked = h; break
if picked is None and hooks:
    picked = hooks[0]; log("event match 실패 → 첫 hook 사용")
if picked is None:
    log("no hooks found (프로젝트가 trusted 이고 root 가 proj 인지 확인)"); sys.exit(4)

print(f"{picked['key']}\t{picked['currentHash']}")
proc.terminate()
