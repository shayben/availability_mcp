"""Minimal stdio MCP server for local user availability."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from availability_mcp import __version__
from availability_mcp.activity import ActivityUnavailable, activity_snapshot

PROTOCOL_VERSION = "2025-06-18"
TOOLS = [
    {
        "name": "get_user_activity",
        "description": (
            "Get the local user's current idle duration and activity state. "
            "Use this to decide whether to wait for user feedback or proceed autonomously."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "idle_threshold_seconds": {
                    "type": "number",
                    "minimum": 0,
                    "default": 300,
                    "description": "Idle duration at which is_idle becomes true.",
                }
            },
            "additionalProperties": False,
        },
    }
]


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "availability-mcp", "version": __version__},
            },
        )
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict) or params.get("name") != "get_user_activity":
            return _error(request_id, -32602, "Unknown tool")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, "Tool arguments must be an object")
        unknown_arguments = arguments.keys() - {"idle_threshold_seconds"}
        if unknown_arguments:
            return _error(request_id, -32602, "Unknown tool argument")
        try:
            threshold = arguments.get("idle_threshold_seconds", 300)
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
                raise ValueError(
                    "idle_threshold_seconds must be a finite non-negative number"
                )
            snapshot = activity_snapshot(threshold)
        except (TypeError, ValueError) as exc:
            return _error(request_id, -32602, str(exc))
        except ActivityUnavailable as exc:
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
        return _result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(snapshot, separators=(",", ":")),
                    }
                ],
                "structuredContent": snapshot,
            },
        )
    if "id" not in message:
        return None
    return _error(request_id, -32601, f"Method not found: {method}")


def serve(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> None:
    for line in input_stream:
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("message must be an object")
            response = handle_request(message)
        except (json.JSONDecodeError, ValueError) as exc:
            response = _error(None, -32700, f"Parse error: {exc}")
        except Exception:
            response = _error(message.get("id"), -32603, "Internal error")
        if response is not None:
            output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
            output_stream.flush()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
