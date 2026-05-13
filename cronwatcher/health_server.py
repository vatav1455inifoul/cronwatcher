"""Tiny HTTP server exposing a /health JSON endpoint."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from cronwatcher.health import HealthChecker


class _Handler(BaseHTTPRequestHandler):
    checker: HealthChecker  # injected by HealthServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/health", "/health/"):
            self.send_response(404)
            self.end_headers()
            return

        report = self.checker.check()
        body = json.dumps(report.to_dict(), indent=2).encode()
        status_code = 200 if report.overall_status == "ok" else 503
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silence default stderr logging
        pass


class HealthServer:
    """Runs the health HTTP server in a daemon thread."""

    def __init__(self, checker: HealthChecker, host: str = "127.0.0.1", port: int = 8080) -> None:
        self._checker = checker
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        handler = type("Handler", (_Handler,), {"checker": self._checker})
        self._server = HTTPServer((self._host, self._port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    @property
    def is_running(self) -> bool:
        """Return True if the server thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def address(self) -> str:
        return f"http://{self._host}:{self._port}/health"
