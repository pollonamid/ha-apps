#!/usr/bin/env bash
# ==============================================================================
# Run the end-to-end tests of the audio_cpp addon
# ==============================================================================
# The tests start the addon image in Docker, synthesize a sentence over the
# Wyoming text-to-speech endpoint and transcribe the audio again over the
# Wyoming speech-to-text endpoint, for every language.
#
# Usage:
#   tests/e2e/run.sh                 # run every scenario
#   tests/e2e/run.sh -k german       # run a single scenario
#   E2E_IMAGE=ghcr.io/... tests/e2e/run.sh
# ==============================================================================
set -euo pipefail

readonly E2E_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${E2E_DIR}/../.." && pwd)"
readonly VENV_DIR="${E2E_DIR}/.cache/venv"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "Creating the virtual environment in ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade pip
    "${VENV_DIR}/bin/pip" install -r "${E2E_DIR}/requirements.txt"
fi

cd "${REPO_ROOT}"
exec "${VENV_DIR}/bin/python" -m pytest "${E2E_DIR}" -v "$@"
