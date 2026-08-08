"""Local HTTP server: iPhone Health Link POSTs samples → SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable

from health_sync import import_health_json_export


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PairingServer:
    def __init__(
        self,
        db_path: Path,
        user_id: str,
        host: str = "0.0.0.0",
        port: int = 8765,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        self.db_path = db_path
        self.user_id = user_id
        self.host = host
        self.port = port
        self.token = str(uuid.uuid4())
        self.on_success = on_success
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def pair_url(self) -> str:
        lan = self.host if self.host != "0.0.0.0" else "127.0.0.1"
        return f"openclaw-health://pair?host={lan}&port={self.port}&token={self.token}"

    def start(self) -> None:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _auth(self) -> bool:
                return self.headers.get("X-Pairing-Token") == server.token

            def do_GET(self) -> None:
                if self.path == "/v1/health/status":
                    body = {"status": "ok", "paired": False, "service": "openclaw-health-bridge"}
                    self._json(200, body)
                else:
                    self.send_error(404)

            def do_POST(self) -> None:
                if self.path != "/v1/health/sync":
                    self.send_error(404)
                    return
                if not self._auth():
                    self.send_error(401)
                    return
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self._json(400, {"status": "error", "message": "Invalid JSON"})
                    return

                tmp = Path("/tmp") / f"openclaw_health_sync_{uuid.uuid4().hex}.json"
                tmp.write_text(json.dumps(payload), encoding="utf-8")
                conn = sqlite3.connect(str(server.db_path))
                try:
                    result = import_health_json_export(conn, tmp, server.user_id)
                finally:
                    conn.close()
                    tmp.unlink(missing_ok=True)

                if result.get("status") == "success" and server.on_success:
                    server.on_success()
                self._json(200, result)

            def _json(self, code: int, obj: dict[str, Any]) -> None:
                data = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._httpd = HTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None
