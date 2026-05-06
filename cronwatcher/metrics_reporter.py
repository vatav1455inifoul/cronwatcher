"""Formats MetricsCollector data into human-readable text tables."""

from typing import Optional

from cronwatcher.metrics import MetricsCollector

_NA = "n/a"


def _fmt_float(value: Optional[float], decimals: int = 1) -> str:
    if value is None:
        return _NA
    return f"{value:.{decimals}f}"


def _fmt_rate(value: Optional[float]) -> str:
    if value is None:
        return _NA
    return f"{value * 100:.1f}%"


class MetricsReport:
    """Renders a summary table of job metrics."""

    HEADER = (
        f"{'Job':<30} {'Runs':>6} {'Missed':>8} "
        f"{'Delayed':>9} {'Avg Delay':>11} {'Max Delay':>11} {'On-Time':>8}"
    )
    SEPARATOR = "-" * len(HEADER)

    def __init__(self, collector: MetricsCollector) -> None:
        self._collector = collector

    def _row(self, name: str) -> str:
        m = self._collector.get(name)
        if m is None:
            return f"{name:<30} {'n/a':>6}"
        return (
            f"{m.job_name:<30} {m.total_runs:>6} {m.missed_count:>8} "
            f"{m.delayed_count:>9} "
            f"{_fmt_float(m.average_delay) + 's':>11} "
            f"{_fmt_float(m.max_delay) + 's':>11} "
            f"{_fmt_rate(m.on_time_rate):>8}"
        )

    def render(self) -> str:
        lines = [self.HEADER, self.SEPARATOR]
        for name in sorted(self._collector.all()):
            lines.append(self._row(name))
        if len(lines) == 2:
            lines.append("  (no data)")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()
