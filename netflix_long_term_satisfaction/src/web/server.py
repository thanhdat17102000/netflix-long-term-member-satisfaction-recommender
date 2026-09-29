from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.web.data_provider import get_payload, get_recommendations, get_user, get_users, search_movies

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8765


class DashboardHandler(SimpleHTTPRequestHandler):
    cache: dict | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print("[web]", self.address_string(), format % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path in {"/", "/index.html"}:
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/health":
            self._json({"ok": True, "url": f"http://{HOST}:{PORT}", "service": "recommender-dashboard"})
            return
        if path.startswith("/api/"):
            self._api(path, query)
            return
        super().do_GET()

    def _api(self, path: str, query: dict[str, list[str]]) -> None:
        payload = self._dashboard()
        try:
            if path == "/api/dashboard":
                result = payload
            elif path == "/api/profile":
                result = {key: payload.get(key) for key in ("profile", "source", "is_full", "disclaimer", "runtime", "generated_at", "partial_full_warning")}
            elif path == "/api/users":
                result = {"items": get_users(payload, _first(query, "q"))}
            elif path.startswith("/api/users/"):
                user_id = int(path.rsplit("/", 1)[-1])
                user = get_user(payload, user_id)
                if user is None:
                    self._json({"error": "user_not_found", "userId": user_id}, status=404)
                    return
                result = {
                    "user": user,
                    "recommendations": {
                        model: get_recommendations(payload, user_id, model, 10)
                        for model in ("popularity", "als", "hybrid")
                    },
                }
            elif path == "/api/recommendations":
                user_id = int(_first(query, "user_id", "0"))
                model = _first(query, "model", "hybrid")
                limit = int(_first(query, "limit", "10"))
                if model not in {"popularity", "als", "hybrid"}:
                    self._json({"error": "model_not_found", "model": model}, status=400)
                    return
                result = {"userId": user_id, "model": model, "items": get_recommendations(payload, user_id, model, limit)}
            elif path == "/api/movies":
                result = {"items": search_movies(payload, _first(query, "query"), _first(query, "genre"), _int_or_none(query, "year_from"), _int_or_none(query, "year_to"))}
            elif path == "/api/models":
                result = {"models": payload.get("models", []), "available_models": payload.get("available_models", [])}
            elif path == "/api/metrics":
                result = {"metrics": payload.get("metrics", {}), "lift": payload.get("satisfaction_lift_vs_popularity")}
            elif path == "/api/pipeline":
                result = {"profile": payload.get("profile"), "stages": payload.get("pipeline", [])}
            elif path == "/api/data-quality":
                result = {"profile": payload.get("profile"), "checks": payload.get("checks", {}), "data_quality": payload.get("data_quality", {})}
            else:
                self._json({"error": "not_found", "path": path}, status=404)
                return
            self._json(result)
        except (TypeError, ValueError) as exc:
            self._json({"error": "bad_request", "message": str(exc)}, status=400)

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _dashboard(self) -> dict:
        if DashboardHandler.cache is None:
            DashboardHandler.cache = get_payload()
        return DashboardHandler.cache


def serve(host: str = HOST, port: int = PORT) -> None:
    DashboardHandler.cache = get_payload()
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard đang chạy tại http://{host}:{port}", flush=True)
    server.serve_forever()


def _first(query: dict[str, list[str]], key: str, default: str = "") -> str:
    values = query.get(key, [])
    return values[0] if values else default


def _int_or_none(query: dict[str, list[str]], key: str) -> int | None:
    value = _first(query, key)
    return int(value) if value else None


if __name__ == "__main__":
    serve()
