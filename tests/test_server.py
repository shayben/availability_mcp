import io
import json
import unittest
from unittest.mock import patch

from availability_mcp.activity import IdleReading
from availability_mcp.server import handle_request, serve


class ServerTests(unittest.TestCase):
    def test_initialize_and_list_tools(self):
        initialized = handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        listed = handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )

        self.assertEqual(initialized["result"]["serverInfo"]["name"], "availability-mcp")
        self.assertEqual(listed["result"]["tools"][0]["name"], "get_user_activity")

    @patch("availability_mcp.activity.read_idle")
    def test_calls_activity_tool(self, read_idle):
        read_idle.return_value = IdleReading(10, "test")

        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_user_activity",
                    "arguments": {"idle_threshold_seconds": 30},
                },
            }
        )

        self.assertFalse(response["result"]["structuredContent"]["is_idle"])
        self.assertEqual(response["result"]["structuredContent"]["idle_seconds"], 10)

    def test_serve_uses_newline_delimited_json(self):
        source = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 4, "method": "ping"}) + "\n"
        )
        destination = io.StringIO()

        serve(source, destination)

        self.assertEqual(json.loads(destination.getvalue())["result"], {})

    def test_rejects_invalid_threshold(self):
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "get_user_activity",
                    "arguments": {"idle_threshold_seconds": float("nan")},
                },
            }
        )

        self.assertEqual(response["error"]["code"], -32602)

    def test_does_not_respond_to_unknown_notification(self):
        response = handle_request(
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {}}
        )

        self.assertIsNone(response)

if __name__ == "__main__":
    unittest.main()
