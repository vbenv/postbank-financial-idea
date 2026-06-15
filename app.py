#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from src.advisor import QUESTION_OPTIONS, advise
from src.evaluation import evaluate
from src.recommender import Customer, recommend


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def _json_response(self, body: dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._json_response({"status": "ok"})
            return
        if self.path == "/api/evaluation":
            self._json_response(evaluate())
            return
        if self.path == "/api/advice/questions":
            self._json_response({"questions": QUESTION_OPTIONS})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/recommend", "/api/advice"}:
            self._json_response({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            values = json.loads(self.rfile.read(length))
            if self.path == "/api/recommend":
                result = recommend(Customer.from_dict(values))
            else:
                result = advise(
                    values["question_id"],
                    Customer.from_dict(values["customer"])
                )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json_response(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="우체국 예금 추천 데모 서버")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"우체국 예금 추천 데모: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
