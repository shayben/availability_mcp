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

## Agent guidance and availability semantics

`get_user_activity` reports a local input-activity signal, not evidence that
the user is interruptible or available. Agents should use it as one signal
when deciding whether to ask a non-urgent question, wait for feedback, or
continue autonomously.

- Treat recent input as `active`, but do not assume an active user is
  available: they may be presenting, in a meeting, or focusing elsewhere.
- Treat an idle reading as support for deferring non-urgent questions or
  continuing reversible work autonomously, without inferring that the user
  has left the device.
- Recheck conservatively rather than polling continuously, for example every
  60 seconds or longer.
- If the source is unavailable, treat availability as unknown rather than
  guessing.
- The `systemd-logind` fallback provides a coarse active/idle signal; its
  duration should not be treated as equivalent to an exact `xprintidle`
  duration.
- Do not store activity history or combine this signal with process, window,
  keystroke, or screen data.

For richer decisions, clients may combine this signal with explicit,
user-controlled local preferences such as quiet hours, do-not-disturb status,
preferred interruption behavior, and an autonomous-work time limit. Any
future calendar integration should be opt-in and expose minimal busy/free
status rather than event details.

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