"""Small dependency-free API for local Feature 1 verification."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from ..db import connect


class Feature1Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/health":
            try:
                with connect() as connection, connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM energy_observations")
                    rows = cursor.fetchone()[0]
                self._json(200, {"status": "ok", "database": "cloud_project", "observation_count": rows})
            except Exception:
                self._json(503, {"status": "unavailable", "database": "cloud_project"})
            return
        self._json(404, {"error": "not found"})


def main() -> None:
    HTTPServer(("127.0.0.1", 8000), Feature1Handler).serve_forever()


if __name__ == "__main__":
    main()
