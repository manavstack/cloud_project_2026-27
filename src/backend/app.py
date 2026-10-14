"""Local API and static-file server for the Feature 1 dashboard."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..db import connect
from ..ml_model.service import dashboard_data, forecast, model_status, train_model

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
FEDERATED_WEIGHTS = Path(__file__).resolve().parents[2] / "results" / "federated_demo" / "weights.json"


class Feature1Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body, allow_nan=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _static(self, name: str) -> None:
        path = FRONTEND / name
        if not path.is_file():
            self._json(404, {"error": "not found"})
            return
        content_type = "text/html; charset=utf-8" if name == "index.html" else (
            "text/javascript; charset=utf-8" if name.endswith(".js") else "text/css; charset=utf-8"
        )
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        request = urlparse(self.path)
        if request.path in ("/", "/index.html"):
            self._static("index.html")
            return
        if request.path in ("/app.js", "/styles.css"):
            self._static(request.path.lstrip("/"))
            return
        if request.path == "/health":
            try:
                with connect() as connection, connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM energy_observations")
                    rows = cursor.fetchone()[0]
                self._json(200, {"status": "ok", "database": "cloud_project", "observation_count": rows})
            except Exception as exc:
                self._json(503, {"status": "unavailable", "error": str(exc)})
            return
        if request.path == "/api/federated":
            try:
                if not FEDERATED_WEIGHTS.is_file():
                    self._json(404, {"error": "Federated weights are unavailable; run python -m src.federated.train"})
                    return
                self._json(200, json.loads(FEDERATED_WEIGHTS.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                self._json(503, {"error": f"Could not load federated weights: {exc}"})
            return
        if request.path == "/api/dashboard":
            try:
                group_key = parse_qs(request.query).get("group", [None])[0]
                self._json(200, dashboard_data(group_key))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(503, {"error": f"Could not load dashboard data: {exc}"})
            return
        if request.path == "/api/model":
            try:
                query = parse_qs(request.query)
                group_key = query.get("group", ["iit_bombay|electricity|Wh|60"])[0]
                asset_id = query.get("asset", [None])[0]
                horizon = int(query.get("horizon", ["24"])[0])
                self._json(200, forecast(group_key, asset_id, horizon))
            except FileNotFoundError as exc:
                self._json(404, {"error": str(exc)})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(503, {"error": f"Could not generate forecast: {exc}"})
            return
        if request.path == "/api/model/status":
            try:
                group_key = parse_qs(request.query).get("group", ["iit_bombay|electricity|Wh|60"])[0]
                self._json(200, model_status(group_key))
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(503, {"error": f"Could not load model status: {exc}"})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/train":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            group_key = body.get("group_key", "iit_bombay|electricity|Wh|60")
            result = train_model(group_key)
            self._json(200, result)
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            self._json(503, {"error": f"Training failed: {exc}"})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Feature1Handler)
    print("FEDRA dashboard available at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
