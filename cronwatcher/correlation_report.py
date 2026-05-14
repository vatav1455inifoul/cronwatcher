"""Text report for correlation groups detected during a watcher run."""
from __future__ import annotations

from typing import List

from cronwatcher.correlation import CorrelationGroup


def _fmt_dt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "—"


class CorrelationReport:
    """Render a human-readable summary of correlation groups."""

    _HEADER = "Correlation Report"
    _SEP = "-" * 50

    def __init__(self, groups: List[CorrelationGroup]) -> None:
        self._groups = groups

    @property
    def systemic_count(self) -> int:
        return sum(1 for g in self._groups if g.is_systemic)

    @property
    def total_count(self) -> int:
        return len(self._groups)

    def render(self) -> str:
        lines: List[str] = [
            self._HEADER,
            self._SEP,
            f"Total windows : {self.total_count}",
            f"Systemic       : {self.systemic_count}",
            self._SEP,
        ]
        if not self._groups:
            lines.append("  (no correlation windows recorded)")
        else:
            for i, group in enumerate(self._groups, start=1):
                tag = "[SYSTEMIC]" if group.is_systemic else "[local]"
                jobs = ", ".join(sorted(set(group.job_names)))
                lines.append(
                    f"  {i:>3}. {tag} "
                    f"{_fmt_dt(group.window_start)} → {_fmt_dt(group.window_end)} "
                    f"| {len(group.alerts)} alert(s) | jobs: {jobs}"
                )
        lines.append(self._SEP)
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()
