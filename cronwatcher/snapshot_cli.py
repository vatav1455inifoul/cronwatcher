"""CLI commands for capturing and viewing watcher snapshots."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronwatcher.loader import load_watcher
from cronwatcher.snapshot import SnapshotCollector
from cronwatcher.snapshot_store import SnapshotStore

_DEFAULT_STORE = Path("cronwatcher_snapshots.jsonl")


def build_snapshot_parser(parent: argparse._SubParsersAction) -> None:
    p = parent.add_parser("snapshot", help="capture and view watcher snapshots")
    sub = p.add_subparsers(dest="snapshot_cmd")

    cap = sub.add_parser("capture", help="capture current state")
    cap.add_argument("--config", required=True, help="path to YAML config")
    cap.add_argument("--store", default=str(_DEFAULT_STORE), help="snapshot file path")
    cap.add_argument("--json", dest="as_json", action="store_true", help="print snapshot as JSON")

    latest = sub.add_parser("latest", help="show the most recent snapshot")
    latest.add_argument("--store", default=str(_DEFAULT_STORE))

    clear = sub.add_parser("clear", help="clear all stored snapshots")
    clear.add_argument("--store", default=str(_DEFAULT_STORE))


def cmd_snapshot_capture(args: argparse.Namespace) -> int:
    watcher = load_watcher(args.config)
    collector = SnapshotCollector(watcher.registry)
    snap = collector.capture()
    store = SnapshotStore(args.store)
    store.save(snap)
    if args.as_json:
        print(json.dumps(snap.to_dict(), indent=2))
    else:
        summary = snap.to_dict()["summary"]
        print(
            f"Snapshot captured at {snap.captured_at.isoformat()}\n"
            f"  total={summary['total']}  ok={summary['ok']}  "
            f"delayed={summary['delayed']}  missed={summary['missed']}"
        )
    return 0


def cmd_snapshot_latest(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.store)
    snap = store.latest()
    if snap is None:
        print("No snapshots found.", file=sys.stderr)
        return 1
    print(json.dumps(snap.to_dict(), indent=2))
    return 0


def cmd_snapshot_clear(args: argparse.Namespace) -> int:
    store = SnapshotStore(args.store)
    store.clear()
    print(f"Cleared snapshots in {args.store}")
    return 0


def dispatch_snapshot(args: argparse.Namespace) -> int:
    dispatch = {
        "capture": cmd_snapshot_capture,
        "latest": cmd_snapshot_latest,
        "clear": cmd_snapshot_clear,
    }
    handler = dispatch.get(args.snapshot_cmd)
    if handler is None:
        print("No snapshot subcommand given. Use --help.", file=sys.stderr)
        return 1
    return handler(args)
