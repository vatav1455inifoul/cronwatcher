"""CLI helpers for managing silence windows (add / list / purge)."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwatcher.silencer import Silencer, SilenceWindow


def _parse_duration(value: str) -> timedelta:
    """Parse a simple duration string like '30m', '2h', '1d'."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = value[-1]
    if unit not in units:
        raise argparse.ArgumentTypeError(
            f"Unknown duration unit {unit!r}. Use s/m/h/d."
        )
    try:
        amount = int(value[:-1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid duration: {value!r}")
    return timedelta(seconds=amount * units[unit])


def build_silence_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher silence",
        description="Manage alert silence windows",
    )
    sub = parser.add_subparsers(dest="silence_cmd")

    add_p = sub.add_parser("add", help="Add a silence window")
    add_p.add_argument("--job", default=None, help="Job name (omit to silence all)")
    add_p.add_argument(
        "--duration", required=True, type=_parse_duration,
        help="Duration e.g. 30m, 2h, 1d",
    )
    add_p.add_argument("--reason", default="", help="Optional reason")

    sub.add_parser("list", help="List active silence windows")
    sub.add_parser("purge", help="Remove expired silence windows")

    return parser


def cmd_silence_add(
    silencer: Silencer,
    job: Optional[str],
    duration: timedelta,
    reason: str,
) -> SilenceWindow:
    now = datetime.now(timezone.utc)
    window = SilenceWindow(
        start=now,
        end=now + duration,
        job_name=job,
        reason=reason,
    )
    silencer.add(window)
    return window


def cmd_silence_list(silencer: Silencer) -> str:
    windows = silencer.active_windows()
    if not windows:
        return "No active silence windows."
    return "\n".join(str(w) for w in windows)


def cmd_silence_purge(silencer: Silencer) -> str:
    removed = silencer.purge_expired()
    return f"Purged {removed} expired window(s). {len(silencer)} remaining."
