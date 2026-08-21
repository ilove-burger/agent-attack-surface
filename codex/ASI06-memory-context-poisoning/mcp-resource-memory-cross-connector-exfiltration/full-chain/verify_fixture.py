#!/usr/bin/env python3
"""Self-check the three-principal MCP fixture without invoking Codex or a model."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SERVER = HERE / "stdio_mcp.py"
SOURCE = HERE / "source-record.md"


class McpProcess:
    def __init__(self, role: str, **paths: Path):
        env = dict(os.environ)
        env["CHAIN_MCP_ROLE"] = role
        for key, value in paths.items():
            env[key] = str(value)
        self.process = subprocess.Popen(
            [sys.executable, str(SERVER)],
            env=env,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        self.next_id = 1

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        assert self.process.stdin and self.process.stdout
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        response = json.loads(self.process.stdout.readline())
        if response.get("id") != request_id or "error" in response:
            raise RuntimeError(f"{method} failed: {response}")
        return response["result"]

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)


def initialize(process: McpProcess) -> dict[str, Any]:
    return process.request(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "fixture-self-check", "version": "1.0"},
        },
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-memory-chain-") as raw:
        work = Path(raw)
        secret = work / "secret.txt"
        sink = work / "observer.jsonl"
        canary = "SYNTHETIC_PRIVATE_FINGERPRINT_8F31"
        secret.write_text(canary + "\n", encoding="utf-8")

        source = McpProcess("source", CHAIN_SOURCE_FILE=SOURCE)
        registry = McpProcess("registry", CHAIN_SECRET_FILE=secret)
        observer = McpProcess("observer", CHAIN_SINK_LOG=sink)
        try:
            source_init = initialize(source)
            registry_init = initialize(registry)
            observer_init = initialize(observer)

            resources = source.request("resources/list")
            resource = source.request(
                "resources/read", {"uri": "issue://hunma/1842"}
            )
            registry_tools = registry.request("tools/list")
            observer_tools = observer.request("tools/list")
            private_result = registry.request(
                "tools/call",
                {"name": "get_release_fingerprint", "arguments": {}},
            )
            observed_value = private_result["content"][0]["text"]
            observer.request(
                "tools/call",
                {
                    "name": "lookup_diagnostic_trace",
                    "arguments": {"trace": observed_value},
                },
            )
        finally:
            source.close()
            registry.close()
            observer.close()

        rows = [
            json.loads(line)
            for line in sink.read_text(encoding="utf-8").splitlines()
            if line
        ]
        checks = {
            "source_has_resource_capability": "resources"
            in source_init.get("capabilities", {}),
            "registry_has_no_resource_capability": "resources"
            not in registry_init.get("capabilities", {}),
            "observer_has_no_resource_capability": "resources"
            not in observer_init.get("capabilities", {}),
            "source_lists_one_issue": len(resources.get("resources", [])) == 1,
            "source_record_loaded": "registry.get_release_fingerprint"
            in resource["contents"][0]["text"],
            "registry_lists_one_tool": len(registry_tools.get("tools", [])) == 1,
            "observer_lists_one_tool": len(observer_tools.get("tools", [])) == 1,
            "synthetic_canary_crossed_connector": len(rows) == 1
            and rows[0].get("trace") == canary,
        }
        result = {
            "schema_version": 1,
            "fixture_only": True,
            "uses_codex_or_model": False,
            "uses_real_secret": False,
            "checks": checks,
            "verdict": "PASS" if all(checks.values()) else "FAIL",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

