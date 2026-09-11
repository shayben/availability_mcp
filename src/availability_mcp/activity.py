"""Cross-platform idle-time detection."""

from __future__ import annotations

import ctypes
import datetime as dt
import math
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Callable


class ActivityUnavailable(RuntimeError):
    """Raised when idle information is unavailable on this device."""


@dataclass(frozen=True)
class IdleReading:
    idle_seconds: float
    source: str


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise ActivityUnavailable(f"{command[0]} could not report idle time") from exc
    return result.stdout


def _linux_idle() -> IdleReading:
    try:
        milliseconds = float(_run(["xprintidle"]).strip())
        return IdleReading(max(0.0, milliseconds / 1000), "xprintidle")
    except (ActivityUnavailable, ValueError):
        pass

    output = _run(
        [
            "loginctl",
            "show-user",
            str(os.getuid()),
            "--property=IdleHint",
            "--property=IdleSinceHintMonotonic",
        ]
    )
    properties = dict(
        line.split("=", 1) for line in output.splitlines() if "=" in line
    )
    if properties.get("IdleHint") != "yes":
        return IdleReading(0.0, "systemd-logind")
    try:
        idle_since = int(properties["IdleSinceHintMonotonic"]) / 1_000_000
    except (KeyError, ValueError) as exc:
        raise ActivityUnavailable("systemd-logind returned incomplete idle data") from exc
    return IdleReading(max(0.0, time.monotonic() - idle_since), "systemd-logind")


def _macos_idle() -> IdleReading:
    output = _run(["ioreg", "-c", "IOHIDSystem"])
    match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', output)
    if not match:
        raise ActivityUnavailable("IOKit returned no HID idle time")
    return IdleReading(int(match.group(1)) / 1_000_000_000, "IOKit")


def _windows_idle() -> IdleReading:
    class LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    try:
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            raise ActivityUnavailable("GetLastInputInfo failed")
        current_tick = ctypes.windll.kernel32.GetTickCount64() & 0xFFFFFFFF
        elapsed_ms = (current_tick - info.dwTime) & 0xFFFFFFFF
    except AttributeError as exc:
        raise ActivityUnavailable("Windows user activity APIs are unavailable") from exc
    return IdleReading(max(0.0, elapsed_ms / 1000), "GetLastInputInfo")


def read_idle() -> IdleReading:
    system = platform.system()
    if system == "Linux":
        return _linux_idle()
    if system == "Darwin":
        return _macos_idle()
    if system == "Windows":
        return _windows_idle()
    raise ActivityUnavailable(f"idle detection is unsupported on {system or 'this platform'}")


def activity_snapshot(
    idle_threshold_seconds: float = 300,
    reader: Callable[[], IdleReading] | None = None,
    now: Callable[[], dt.datetime] | None = None,
) -> dict[str, object]:
    if not math.isfinite(idle_threshold_seconds) or idle_threshold_seconds < 0:
        raise ValueError("idle_threshold_seconds must be a finite non-negative number")

    observed_at = (now or (lambda: dt.datetime.now(dt.timezone.utc)))()
    reading = (reader or read_idle)()
    if not math.isfinite(reading.idle_seconds):
        raise ActivityUnavailable("idle source returned an invalid duration")
    idle_seconds = max(0.0, reading.idle_seconds)
    last_activity_at = observed_at - dt.timedelta(seconds=idle_seconds)
    return {
        "is_idle": idle_seconds >= idle_threshold_seconds,
        "idle_seconds": round(idle_seconds, 3),
        "idle_threshold_seconds": idle_threshold_seconds,
        "last_activity_at": last_activity_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "source": reading.source,
    }
