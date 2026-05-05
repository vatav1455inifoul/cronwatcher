"""Simple CLI entry point for cronwatcher reporting."""

import argparse
import sys
from datetime import datetime

from cronwatcher.registry import JobRegistry
from cronwatcher.reporter import Reporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher",
        description="Monitor cron job execution and report status.",
    )
    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="Print a status report")
    report_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    return parser


def cmd_report(registry: JobRegistry, fmt: str) -> int:
    reporter = Reporter(registry)
    summary = reporter.generate()
    if fmt == "json":
        import json
        data = {
            "generated_at": summary.generated_at.isoformat(),
            "total": summary.total,
            "missed": summary.missed_count,
            "delayed": summary.delayed_count,
            "healthy": summary.healthy_count,
            "jobs": [
                {
                    "name": j.job_name,
                    "status": j.status_label(),
                    "last_run": j.last_run.isoformat() if j.last_run else None,
                    "run_count": j.run_count,
                    "delay_seconds": j.delay_seconds,
                }
                for j in summary.jobs
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print(summary)
    return 0


def main(argv=None, registry: JobRegistry = None) -> int:
    if registry is None:
        registry = JobRegistry()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "report":
        return cmd_report(registry, args.format)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
