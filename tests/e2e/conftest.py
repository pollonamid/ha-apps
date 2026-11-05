"""Fixtures for the end-to-end tests of the audio_cpp addon.

The tests run the real addon image in Docker. The addon reads its options
from the Home Assistant Supervisor API, so a mock Supervisor is started on the
host and the container is pointed at it with ``--add-host supervisor:host-gateway``.

The models are downloaded into the shared ``/share`` directory of the container.
That directory is kept between runs in ``tests/e2e/.cache/share``, so the
models are downloaded only once.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = REPO_ROOT / "audio_cpp"
E2E_DIR = Path(__file__).resolve().parent
CACHE_DIR = E2E_DIR / ".cache"
SHARE_DIR = CACHE_DIR / "share"
MODELS_DIR = SHARE_DIR / "audio_cpp" / "models"

BUILT_IMAGE = "ha-apps-e2e/audio-cpp:e2e"
SUPERVISOR_TOKEN = "e2e-supervisor-token"
SUPERVISOR_PORT = 8123

CONTAINER_HTTP_PORT = 8099
CONTAINER_ASR_PORT = 11301
CONTAINER_TTS_PORT = 11201

READY_TIMEOUT = 30 * 60
POLL_INTERVAL = 5.0


@dataclass(frozen=True)
class Scenario:
    """One language scenario of the round trip test."""

    name: str
    tts_language: str
    asr_language: str
    text: str


SCENARIOS: dict[str, Scenario] = {
    "english": Scenario(
        name="english",
        tts_language="en",
        asr_language="en",
        text="The quick brown fox jumps over the lazy dog.",
    ),
    "german": Scenario(
        name="german",
        tts_language="de",
        asr_language="de",
        text="Das ist ein Test der Spracherkennung.",
    ),
}

ASR_MODEL = "qwen3_asr_0_6b_q8_0"

MODEL_FILES: dict[str, str] = {
    ASR_MODEL: "Qwen3-ASR-0.6B-GGUF/qwen3-asr-0.6b-q8_0.gguf",
}



class Addon:
    """A running addon container with the host ports it is reachable at."""

    def __init__(self, name: str, http_port: int, asr_port: int, tts_port: int) -> None:
        self.name = name
        self.http_port = http_port
        self.asr_port = asr_port
        self.tts_port = tts_port

    @property
    def health_url(self) -> str:
        """URL of the health endpoint of the HTTP API."""
        return f"http://127.0.0.1:{self.http_port}/health"


def run_docker(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a docker command and return the result."""
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


def docker_logs(name: str) -> str:
    """Return the logs of a container."""
    result = run_docker(["logs", name], check=False)
    return result.stdout + result.stderr


def free_port() -> int:
    """Return a free TCP port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check whether a TCP port accepts a connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_is_ok(url: str, timeout: float = 2.0) -> bool:
    """Check whether an HTTP endpoint answers with 200."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def model_path(package_id: str) -> Path:
    """Return the host path of the model file of a package."""
    return MODELS_DIR / MODEL_FILES[package_id]


def build_options(scenario: Scenario) -> dict[str, Any]:
    """Build the addon options of a scenario."""
    return {
        "speech_to_text_model": ASR_MODEL,
        "backend": "cpu",
        "threads": 4,
        "max_loaded_models": 2,
        "tts_family": "pocket_tts",
        "hf_token": "",
    }


@pytest.fixture(scope="session")
def image() -> str:
    """The addon image under test, built locally unless E2E_IMAGE is set."""
    existing = os.environ.get("E2E_IMAGE")
    if existing:
        print(f"\n[fixture image] using {existing}")
        return existing

    print(f"\n[fixture image] building {BUILT_IMAGE}")
    result = run_docker(
        ["build", "-t", BUILT_IMAGE, "-f", "audio_cpp/Dockerfile", "audio_cpp"],
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"Building {BUILT_IMAGE} failed:\n{result.stdout}\n{result.stderr}")
    return BUILT_IMAGE


@pytest.fixture(scope="session")
def share_dir() -> Path:
    """The shared directory of the container, kept between runs."""
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    return SHARE_DIR


@pytest.fixture(scope="session")
def options_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The file the mock Supervisor reads the addon options from."""
    path = tmp_path_factory.mktemp("supervisor") / "options.json"
    path.write_text(json.dumps(build_options(SCENARIOS["english"])), encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def docker_network() -> Iterator[str]:
    """A docker network for the containers of the test."""
    name = "audio-cpp-e2e"
    run_docker(["network", "create", name], check=False)
    try:
        yield name
    finally:
        run_docker(["network", "rm", name], check=False)


@pytest.fixture(scope="session")
def mock_supervisor(
    options_file: Path,
    image: str,
    docker_network: str,
) -> Iterator[str]:
    """A mock Supervisor API in a container of the test network.

    It runs in a container, so the addon container can reach it by its name.
    The directory with the options file is mounted into it, so the options can
    be changed between the scenarios.
    """
    name = "audio-cpp-e2e-supervisor"
    run_docker(["rm", "-f", name], check=False)
    run_docker(
        [
            "run",
            "-d",
            "--name",
            name,
            "--network",
            docker_network,
            "--network-alias",
            "supervisor",
            "--entrypoint",
            "/usr/bin/python3",
            "-v",
            f"{options_file.parent}:/supervisor",
            "-v",
            f"{E2E_DIR}:/e2e:ro",
            image,
            "/e2e/mock_supervisor.py",
            "--options",
            "/supervisor/options.json",
            "--host",
            "0.0.0.0",
            "--port",
            str(SUPERVISOR_PORT),
            "--token",
            SUPERVISOR_TOKEN,
        ]
    )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            logs = docker_logs(name)
            if "listening" in logs:
                break
            if "Traceback" in logs:
                pytest.fail(f"The mock Supervisor died:\n{logs}")
            time.sleep(0.5)
        else:
            pytest.fail(f"The mock Supervisor did not start:\n{docker_logs(name)}")
        print(f"\n[fixture mock_supervisor] {name} is ready")
        yield "supervisor"
    finally:
        run_docker(["rm", "-f", name], check=False)


@pytest.fixture(params=sorted(SCENARIOS), ids=sorted(SCENARIOS))
def scenario(request: pytest.FixtureRequest) -> Scenario:
    """The scenario under test."""
    return SCENARIOS[request.param]


def wait_for_ready(addon: Addon, packages: list[str]) -> None:
    """Wait until the container serves its ports and has the models on disk."""
    deadline = time.monotonic() + READY_TIMEOUT
    reported = ""
    while time.monotonic() < deadline:
        problems = []
        if not port_is_open("127.0.0.1", addon.asr_port):
            problems.append(f"port {addon.asr_port} is closed")
        if not port_is_open("127.0.0.1", addon.tts_port):
            problems.append(f"port {addon.tts_port} is closed")
        if not http_is_ok(addon.health_url):
            problems.append(f"{addon.health_url} is not ready")
        for package in packages:
            path = model_path(package)
            if not path.exists():
                problems.append(f"{path.name} is missing")

        if not problems:
            return

        # The container died, there is no point in waiting for it.
        if run_docker(["inspect", "-f", "{{.State.Running}}", addon.name], check=False).stdout.strip() != "true":
            raise RuntimeError(
                f"The container {addon.name} stopped:\n{docker_logs(addon.name)}"
            )

        report = ", ".join(problems)
        if report != reported:
            print(f"\n[fixture addon] waiting: {report}")
            reported = report
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(
        f"The addon did not become ready within {READY_TIMEOUT} seconds:\n"
        f"{reported}\n\n{docker_logs(addon.name)}"
    )


@pytest.fixture
def addon(
    scenario: Scenario,
    image: str,
    share_dir: Path,
    mock_supervisor: str,
    docker_network: str,
    options_file: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Addon]:
    """A running addon container for the scenario under test."""
    options_file.write_text(json.dumps(build_options(scenario)), encoding="utf-8")

    data_dir = tmp_path_factory.mktemp(f"data-{scenario.name}")
    config_dir = tmp_path_factory.mktemp(f"config-{scenario.name}")
    (data_dir / "options.json").write_text(
        json.dumps(build_options(scenario)), encoding="utf-8"
    )

    name = f"audio-cpp-e2e-{scenario.name}"
    run_docker(["rm", "-f", name], check=False)

    http_port = free_port()
    asr_port = free_port()
    tts_port = free_port()

    run_docker(
        [
            "run",
            "-d",
            "--name",
            name,
            "--network",
            docker_network,
            "-e",
            f"SUPERVISOR_API=http://supervisor:{SUPERVISOR_PORT}",
            "-e",
            f"SUPERVISOR_TOKEN={SUPERVISOR_TOKEN}",
            "-v",
            f"{data_dir}:/data",
            "-v",
            f"{config_dir}:/config",
            "-v",
            f"{share_dir}:/share",
            "-p",
            f"127.0.0.1:{http_port}:{CONTAINER_HTTP_PORT}",
            "-p",
            f"127.0.0.1:{asr_port}:{CONTAINER_ASR_PORT}",
            "-p",
            f"127.0.0.1:{tts_port}:{CONTAINER_TTS_PORT}",
            image,
        ]
    )

    addon = Addon(name, http_port, asr_port, tts_port)
    try:
        wait_for_ready(addon, [ASR_MODEL])
    except Exception:
        print(f"\n[fixture addon] container logs:\n{docker_logs(name)}")
        raise
    print(f"\n[fixture addon] {name} is ready ({addon.health_url})")
    yield addon
    run_docker(["rm", "-f", name], check=False)
