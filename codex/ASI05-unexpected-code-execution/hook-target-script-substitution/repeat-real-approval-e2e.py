#!/usr/bin/env python3
"""Repeat the real Codex hook approval E2E and export stability evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
DRIVER = HERE / "poc-real-approval-e2e.py"
DEFAULT_CODEX = Path(
    "/home/mjhy3/agent/hunma_agent/harness/targets/"
    "codex-0.148.0-fresh-npm/package/vendor/"
    "x86_64-unknown-linux-musl/bin/codex"
)
DEFAULT_WORK_ROOT = Path(
    "/home/mjhy3/agent/hunting-box/work/"
    "codex-hook-real-approval-stability"
)
DEFAULT_GIT_PULL_WORK_ROOT = Path(
    "/home/mjhy3/agent/hunting-box/work/"
    "codex-hook-git-pull-stability-v2"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def one_line(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lines = value.splitlines()
    return lines[0] if lines else ""


def summarize_result(
    approval: str,
    run_number: int,
    run_dir: Path,
    elapsed: float,
    process: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    result_path = run_dir / "result.json"
    record: dict[str, Any] = {
        "approval": approval,
        "run": run_number,
        "run_dir": str(run_dir),
        "result_path": str(result_path),
        "driver_returncode": process.returncode,
        "duration_seconds": round(elapsed, 3),
    }
    if not result_path.is_file():
        record.update(
            {
                "pass": False,
                "error": "result.json was not generated",
                "before": None,
                "after_approval": None,
                "after_swap": None,
                "hash_unchanged_after_swap": False,
                "marker_observed": False,
            }
        )
        return record

    data = json.loads(result_path.read_text(encoding="utf-8"))
    record.update(
        {
            "approval_transport": data.get("approval_transport"),
            "substitution": data.get("substitution", "direct"),
            "codex_version": data.get("codex_version"),
            "codex_sha256": data.get("codex_sha256"),
            "bypass_flag_used": data.get("bypass_flag_used"),
            "before": (data.get("before") or {}).get("trustStatus"),
            "after_approval": (data.get("after_approval") or {}).get(
                "trustStatus"
            ),
            "after_swap": (data.get("after_swap") or {}).get("trustStatus"),
            "hash_unchanged_after_swap": (
                data.get("substitution_checks") or {}
            ).get("hash_unchanged", False),
            "key_unchanged_after_swap": (
                data.get("substitution_checks") or {}
            ).get("key_unchanged", False),
            "marker_observed": data.get("marker_observed", False),
            "delivery_checks": data.get("delivery_checks") or {},
            "changed_files": (data.get("delivery") or {}).get("changed_files"),
            "exec_returncode": data.get("exec_returncode"),
            "whoami": one_line(data.get("whoami")),
            "pass": process.returncode == 0 and data.get("pass") is True,
        }
    )
    return record


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Codex hook 실제 승인 E2E 반복 결과",
        "",
        f"- 생성 시각(UTC): `{summary['finished_at']}`",
        f"- Codex: `{summary.get('codex_version')}`",
        f"- Binary SHA-256: `{summary.get('codex_sha256')}`",
        f"- 스크립트 전달 방식: `{summary['substitution']}`",
        f"- 반복: UI `{summary['repeat']}`회 + API `{summary['repeat']}`회",
        f"- 통과: `{summary['passed_runs']}/{summary['total_runs']}`",
        f"- 안정성 판정: `{'PASS' if summary['stability_pass'] else 'FAIL'}`",
        "",
        "| 승인 | Run | 결과 | 승인 전 | 승인 후 | 치환 후 | Hash 불변 | 전달 검증 | Marker | Exec RC | 시간(초) | run_dir |",
        "|---|---:|---|---|---|---|---|---|---|---:|---:|---|",
    ]
    for run in summary["runs"]:
        lines.append(
            "| {approval} | {run} | {result} | {before} | {after_approval} | "
            "{after_swap} | {hash_same} | {delivery} | {marker} | {exec_rc} | {duration} | "
            "`{run_dir}` |".format(
                approval=run["approval"].upper(),
                run=run["run"],
                result="PASS" if run["pass"] else "FAIL",
                before=run.get("before"),
                after_approval=run.get("after_approval"),
                after_swap=run.get("after_swap"),
                hash_same=run.get("hash_unchanged_after_swap"),
                delivery=all(run.get("delivery_checks", {}).values()),
                marker=run.get("marker_observed"),
                exec_rc=run.get("exec_returncode"),
                duration=run["duration_seconds"],
                run_dir=run["run_dir"],
            )
        )
    lines.extend(
        [
            "",
            "각 run은 별도의 project, fake HOME, CODEX_HOME 및 outside marker 디렉터리를 사용한다.",
            "UI/API 승인 전후와 스크립트 치환 후 상태는 매번 app-server `hooks/list`로 재조회했다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--codex", type=Path, default=DEFAULT_CODEX)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument(
        "--substitution",
        choices=("direct", "git-pull"),
        default="direct",
    )
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    codex = args.codex.resolve()
    if not codex.is_file():
        parser.error(f"Codex binary not found: {codex}")
    work_root = (
        args.work_root
        if args.work_root is not None
        else (
            DEFAULT_GIT_PULL_WORK_ROOT
            if args.substitution == "git-pull"
            else DEFAULT_WORK_ROOT
        )
    ).resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    runs: list[dict[str, Any]] = []

    for approval in ("ui", "api"):
        for run_number in range(1, args.repeat + 1):
            run_dir = work_root / approval / f"run-{run_number:02d}"
            command = [
                sys.executable,
                str(DRIVER),
                "--approval",
                approval,
                "--codex",
                str(codex),
                "--run-dir",
                str(run_dir),
                "--substitution",
                args.substitution,
            ]
            print(
                f"[{approval.upper()} {run_number}/{args.repeat}] {run_dir}",
                flush=True,
            )
            started = time.monotonic()
            process = subprocess.run(command, capture_output=True, text=True)
            elapsed = time.monotonic() - started
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "repeat-driver.log").write_text(
                process.stdout + process.stderr, encoding="utf-8"
            )
            record = summarize_result(
                approval, run_number, run_dir, elapsed, process
            )
            runs.append(record)
            print(
                f"  {'PASS' if record['pass'] else 'FAIL'} "
                f"marker={record.get('marker_observed')} "
                f"after_swap={record.get('after_swap')} "
                f"duration={record['duration_seconds']}s",
                flush=True,
            )

    versions = sorted(
        {run["codex_version"] for run in runs if run.get("codex_version")}
    )
    hashes = sorted(
        {run["codex_sha256"] for run in runs if run.get("codex_sha256")}
    )
    passed_runs = sum(run["pass"] for run in runs)
    summary = {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": utc_now(),
        "repeat": args.repeat,
        "substitution": args.substitution,
        "total_runs": len(runs),
        "passed_runs": passed_runs,
        "failed_runs": len(runs) - passed_runs,
        "stability_pass": passed_runs == len(runs),
        "codex": str(codex),
        "codex_version": versions[0] if len(versions) == 1 else versions,
        "codex_sha256": hashes[0] if len(hashes) == 1 else hashes,
        "environment": {
            "platform": platform.platform(),
            "kernel": os.uname().release,
            "python": platform.python_version(),
        },
        "by_approval": {
            approval: {
                "total": sum(run["approval"] == approval for run in runs),
                "passed": sum(
                    run["approval"] == approval and run["pass"] for run in runs
                ),
            }
            for approval in ("ui", "api")
        },
        "runs": runs,
    }
    (work_root / "results.jsonl").write_text(
        "".join(json.dumps(run, ensure_ascii=False) + "\n" for run in runs),
        encoding="utf-8",
    )
    (work_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (work_root / "summary.md").write_text(
        markdown_summary(summary), encoding="utf-8"
    )
    print(
        f"\nSTABILITY {'PASS' if summary['stability_pass'] else 'FAIL'}: "
        f"{passed_runs}/{len(runs)}\nsummary: {work_root / 'summary.json'}",
        flush=True,
    )
    return 0 if summary["stability_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
