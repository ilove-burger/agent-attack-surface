#!/usr/bin/env python3
# loopback mock OpenAI Responses API for the Codex hook E2E.
#   usage: e2e-mock.py PORT [text|shell]
#   text  -> assistant message, turn completes (fires SessionStart hooks)
#   shell -> emits a shell function_call (fires PreToolUse hooks)
import sys, json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1])
MODE = sys.argv[2] if len(sys.argv) > 2 else "text"


def sse(evs):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in evs).encode()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        if n:
            self.rfile.read(n)
        items = [{"type": "response.created", "response": {"id": "r1"}}]
        if MODE == "shell":
            items.append({"type": "response.output_item.done", "item": {
                "type": "function_call", "call_id": "c1", "name": "shell",
                "arguments": json.dumps({"command": ["true"]})}})
        else:
            items.append({"type": "response.output_item.done", "item": {
                "type": "message", "role": "assistant", "id": "m1",
                "content": [{"type": "output_text", "text": "done"}]}})
        items.append({"type": "response.completed", "response": {"id": "r1", "usage": {
            "input_tokens": 0, "input_tokens_details": None, "output_tokens": 0,
            "output_tokens_details": None, "total_tokens": 0}}})
        body = sse(items)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


HTTPServer(("127.0.0.1", PORT), H).serve_forever()
