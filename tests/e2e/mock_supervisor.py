"""Minimal stand-in for the Home Assistant Supervisor API.

The audio_cpp addon reads its options with bashio, which asks the Supervisor
for ``/addons/self/options/config`` and expects the answer in the form
``{"result": "ok", "data": {...}}``. Outside of Home Assistant there is no
Supervisor, so this server answers that single request with the content of a
JSON file. The file is re-read on every request, so a test can change the
options between scenarios without restarting the server.

Start it with::

    python mock_supervisor.py --options options.json --port 8123
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

CONFIG_PATH = "/addons/self/options/config"


class SupervisorHandler(BaseHTTPRequestHandler):
    """Answers the addon options request of the Supervisor API."""

    options_file: Path
    token: str

    def do_GET(self) -> None:  # noqa: N802 - name comes from BaseHTTPRequestHandler
        if self.path.split("?")[0] != CONFIG_PATH:
            self._reply(404, {"result": "error", "message": f"Unknown resource {self.path}"})
            return

        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self._reply(401, {"result": "error", "message": "Invalid access token"})
            return

        try:
            options = json.loads(self.options_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self._reply(500, {"result": "error", "message": str(exc)})
            return

        self._reply(200, {"result": "ok", "data": options})

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write(f"mock-supervisor: {fmt % args}\n")
        sys.stdout.flush()


def build_server(options_file: Path, host: str, port: int, token: str) -> ThreadingHTTPServer:
    """Create the HTTP server for the given options file."""
    handler = type(
        "BoundSupervisorHandler",
        (SupervisorHandler,),
        {"options_file": options_file, "token": token},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main() -> int:
    """Serve the addon options until the process is killed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--options", required=True, type=Path, help="JSON file with the addon options")
    parser.add_argument("--host", default="0.0.0.0", help="address to listen on")
    parser.add_argument("--port", required=True, type=int, help="port to listen on")
    parser.add_argument("--token", default="", help="expected bearer token")
    args = parser.parse_args()

    server = build_server(args.options, args.host, args.port, args.token)
    sys.stdout.write(f"mock-supervisor: listening on {args.host}:{args.port}\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
