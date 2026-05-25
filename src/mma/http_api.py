"""Tiny stdlib HTTP API for local integrations."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mma.services import MmaService


class ApiHandler(BaseHTTPRequestHandler):
    service: MmaService

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API.
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self._json(200, {"status": "ok"})
            elif path == "/tasks":
                self._json(200, self.service.list_tasks())
            elif path == "/capabilities":
                self._json(200, self.service.capabilities())
            elif path == "/resources":
                self._json(200, self.service.resource_status())
            else:
                self._json(404, {"error": "not found"})
        except Exception as exc:  # noqa: BLE001 - API boundary reports all errors as JSON.
            self._json(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API.
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/tasks":
                self._json(
                    201,
                    self.service.create_task(
                        description=body["description"],
                        title=body.get("title"),
                        task_type=body.get("task_type", "code"),
                        risk=body.get("risk", "normal"),
                        validation_profile=body.get("validation_profile", "python"),
                    ),
                )
            elif path == "/run":
                self._json(200, self.service.run_task(body["task_id"], body.get("model")))
            elif path == "/assets/answer":
                self._json(200, self.service.answer_asset(body["request_id"], body["answer"]))
            elif path == "/memory/index":
                self._json(200, self.service.index_memory())
            else:
                self._json(404, {"error": "not found"})
        except KeyError as exc:
            self._json(400, {"error": f"missing field: {exc.args[0]}"})
        except Exception as exc:  # noqa: BLE001 - API boundary reports all errors as JSON.
            self._json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature.
        return

    def _read_json(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0"))
        if size == 0:
            return {}
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def _json(self, status: int, payload: Any) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(repo: Path, host: str, port: int) -> ThreadingHTTPServer:
    service = MmaService(repo)
    service.init()

    class Handler(ApiHandler):
        pass

    Handler.service = service
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mma-api")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    serve(Path(args.repo), args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
