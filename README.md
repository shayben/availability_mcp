# availability_mcp

A dependency-free MCP server that runs locally and reports the current user's
activity/idle state. Agents can use it when deciding whether to wait for user
feedback or continue autonomously. Activity data stays on-device and is only
returned to the connected MCP client.

## Install and configure

Python 3.10 or newer is required.

```bash
python -m pip install .
```

Add the server to your MCP client:

```json
{
  "mcpServers": {
    "availability": {
      "command": "availability-mcp"
    }
  }
}
```

For development, run it directly with:

```bash
PYTHONPATH=src python -m availability_mcp.server
```

## Tool

### `get_user_activity`

Returns:

- `idle_seconds`: time since the last detected user input
- `is_idle`: whether idle time meets `idle_threshold_seconds` (default: 300)
- `last_activity_at` and `observed_at`: UTC ISO 8601 timestamps
- `source`: the operating-system API used for the reading

The optional `idle_threshold_seconds` argument must be non-negative.

## Platform support

- **Windows:** `GetLastInputInfo`
- **macOS:** the built-in `ioreg` utility and `IOHIDSystem`
- **Linux:** `xprintidle` when installed, otherwise systemd-logind's user idle
  hint. Desktop environments that publish neither source return a tool error
  rather than guessing.

On macOS, terminal input-monitoring permissions may be required. Linux
systemd-logind reports coarse active/idle state when `xprintidle` is not
available; install `xprintidle` under X11 for exact idle duration.

## Test

```bash
PYTHONPATH=src python -m unittest discover -s tests
```