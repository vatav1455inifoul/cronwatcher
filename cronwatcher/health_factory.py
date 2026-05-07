"""Factory helpers for wiring up health checking."""
from __future__ import annotations

from cronwatcher.health import HealthChecker
from cronwatcher.health_server import HealthServer


def build_health_server(
    registry,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> HealthServer:
    """Create and return a (not yet started) HealthServer for *registry*."""
    checker = HealthChecker(registry)
    return HealthServer(checker, host=host, port=port)


def start_health_server(
    registry,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> HealthServer:
    """Create, start, and return a HealthServer for *registry*."""
    server = build_health_server(registry, host=host, port=port)
    server.start()
    return server
