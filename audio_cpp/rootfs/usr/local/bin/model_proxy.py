#!/opt/wyoming/bin/python
"""Serve the requests of the Wyoming bridges and install the models on demand.

The bridges of the app send the model and the voice of a request to
audio.cpp. The models of the text-to-speech family are not all installed, a
model and its voice are downloaded when they are used for the first time.

This proxy sits between the bridges and audio.cpp. It installs what a
request needs and then forwards the request.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("model-proxy")

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/share/audio_cpp/models"))
TOKEN_FILE = Path(os.environ.get("TOKEN_FILE", "/root/.cache/huggingface/token"))
HF_BASE_URL = os.environ.get("HF_BASE_URL", "https://huggingface.co")
HF_REPO = os.environ.get("HF_REPO", "")
HF_REVISION = os.environ.get("HF_REVISION", "main")
MODEL_MANAGER = os.environ.get("MODEL_MANAGER", "/app/audiocpp_model_manager")

LISTEN_HOST = os.environ.get("LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "8098"))
TARGET_HOST = os.environ.get("TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.environ.get("TARGET_PORT", "8099"))

# The installs are serialised, so a model is not downloaded twice.
INSTALL_LOCK = threading.Lock()


def auth_header() -> dict[str, str]:
    """Return the authorization header for the model repository."""
    try:
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    return {"Authorization": f"Bearer {token}"} if token else {}


def install_model(package: str) -> bool:
    """Download a model package. Returns True when it is installed."""
    with INSTALL_LOCK:
        if model_installed(package):
            return True

        LOGGER.info("Installing the model %s", package)
        result = subprocess.run(
            [
                MODEL_MANAGER,
                "install",
                package,
                "--models-dir",
                str(MODELS_DIR),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            LOGGER.error(
                "Could not install the model %s: %s", package, result.stderr.strip()
            )
            return False

        LOGGER.info("The model %s is installed", package)
        return True


def model_installed(package: str) -> bool:
    """Check whether the model of a package is on the disk."""
    result = subprocess.run(
        [
            MODEL_MANAGER,
            "info",
            package,
            "--models-dir",
            str(MODELS_DIR),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        packages = json.loads(result.stdout)
    except ValueError:
        return False
    return bool(packages and packages[0].get("installed"))


def install_voice(path: str) -> bool:
    """Download a voice file. Returns True when it is on the disk."""
    voice = Path(path)
    if voice.exists() and voice.stat().st_size > 0:
        return True

    try:
        relative = voice.relative_to(MODELS_DIR)
    except ValueError:
        LOGGER.error("The voice %s is not in the models directory", path)
        return False

    if not HF_REPO:
        LOGGER.error("No model repository is known for the voice %s", path)
        return False

    url = f"{HF_BASE_URL}/{HF_REPO}/resolve/{HF_REVISION}/{relative}"
    LOGGER.info("Downloading the voice %s", relative)
    voice.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=auth_header()), timeout=300
        ) as response:
            voice.write_bytes(response.read())
    except (urllib.error.URLError, OSError) as exc:
        LOGGER.error("Could not download the voice %s: %s", relative, exc)
        return False

    LOGGER.info("The voice %s is installed", relative)
    return True


def prepare(body: bytes) -> bytes:
    """Install the model and the voice of a request."""
    try:
        payload: dict[str, Any] = json.loads(body)
    except ValueError:
        return body

    model = payload.get("model")
    if isinstance(model, str) and model:
        install_model(model)

    options = payload.get("options")
    if isinstance(options, dict):
        embedding = options.get("voice_embedding_file")
        if isinstance(embedding, str) and embedding:
            install_voice(embedding)

    return body


class ProxyHandler(BaseHTTPRequestHandler):
    """Forwards the requests to audio.cpp."""

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        """Send the log to the service log."""
        LOGGER.debug(fmt, *args)

    def _forward(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        if method == "POST" and self.path.startswith("/v1/audio/speech"):
            body = prepare(body)

        url = f"http://{TARGET_HOST}:{TARGET_PORT}{self.path}"
        request = urllib.request.Request(
            url, data=body if body else None, method=method
        )
        for key, value in self.headers.items():
            if key.lower() not in ("host", "content-length", "connection"):
                request.add_header(key, value)

        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                payload = response.read()
                self.send_response(response.status)
                content_type = response.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (urllib.error.URLError, OSError) as exc:
            LOGGER.error("Could not forward the request: %s", exc)
            payload = json.dumps({"error": {"message": str(exc)}}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - name comes from BaseHTTPRequestHandler
        """Forward a GET request."""
        self._forward("GET")

    def do_POST(self) -> None:  # noqa: N802 - name comes from BaseHTTPRequestHandler
        """Forward a POST request."""
        self._forward("POST")


def main() -> int:
    """Serve the proxy until the service is stopped."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    server.daemon_threads = True
    LOGGER.info(
        "The model proxy listens on %s:%s and forwards to %s:%s",
        LISTEN_HOST,
        LISTEN_PORT,
        TARGET_HOST,
        TARGET_PORT,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
