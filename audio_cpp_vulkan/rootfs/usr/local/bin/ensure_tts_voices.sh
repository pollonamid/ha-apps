#!/usr/bin/env bash
# ==============================================================================
# Download the voice embeddings of a text-to-speech model
# ==============================================================================
# The Wyoming text-to-speech bridge needs a voice embedding for the model.
# The PocketTTS models of the languages other than English do not ship one in
# their package, and without an embedding the synthesis fails with
# "requires a session voice".
#
# The model repository holds the voices of every language, so the embeddings
# of the language of the model are downloaded from there. The voice that is
# configured in the app options is fetched right away, the other voices of the
# language are downloaded in the background.
#
# Usage: ensure_tts_voices.sh <model package id> <voice name>
#        ensure_tts_voices.sh <model package id> <voice name> --worker
# ==============================================================================
set -uo pipefail

MODELS_DIR="${MODELS_DIR:-/share/audio_cpp/models}"
SPEC_DIR="${SPEC_DIR:-/app/model_specs}"
TOKEN_FILE="${TOKEN_FILE:-/root/.cache/huggingface/token}"
HF_BASE_URL="${HF_BASE_URL:-https://huggingface.co}"

MODEL_ID="${1:-}"
VOICE="${2:-}"
MODE="${3:-}"

if [[ -z "${MODEL_ID}" || -z "${VOICE}" ]]; then
    echo "ensure_tts_voices: usage: $0 <model package id> <voice name>" >&2
    exit 2
fi

# The file names of the embeddings are lower case.
VOICE_FILE_NAME="${VOICE,,}.safetensors"

# Find the spec file that owns the model package id.
spec_file=""
for candidate in "${SPEC_DIR}"/*.json; do
    if jq -e --arg id "${MODEL_ID}" '.packages[]? | select(.id == $id)' "${candidate}" > /dev/null 2>&1; then
        spec_file="${candidate}"
        break
    fi
done

if [[ -z "${spec_file}" ]]; then
    echo "ensure_tts_voices: unknown model '${MODEL_ID}'" >&2
    exit 1
fi

target_dir="$(jq -r --arg id "${MODEL_ID}" '.packages[] | select(.id == $id) | .target_directory' "${spec_file}")"
if [[ -z "${target_dir}" || "${target_dir}" == "null" ]]; then
    exit 0
fi

repo="$(jq -r '.package_defaults.download.repo // empty' "${spec_file}")"
revision="$(jq -r '.package_defaults.download.revision // "main"' "${spec_file}")"

model_dir="${MODELS_DIR}/${target_dir}"
voice_dir="${model_dir}/embeddings"
lock_file="${model_dir}/.voices.lock"

if [[ -z "${repo}" ]]; then
    # No repository is known, so the only chance is a voice that is already
    # installed for another model.
    installed="$(find "${MODELS_DIR}" -type f -path "*/embeddings/${VOICE_FILE_NAME}" -print -quit 2> /dev/null || true)"
    if [[ -n "${installed}" ]]; then
        mkdir -p "${voice_dir}"
        cp -f "${installed}" "${voice_dir}/${VOICE_FILE_NAME}.part.$$"
        mv "${voice_dir}/${VOICE_FILE_NAME}.part.$$" "${voice_dir}/${VOICE_FILE_NAME}"
        echo "ensure_tts_voices: copied the voice '${VOICE}' from ${installed}"
    fi
    exit 0
fi

auth=()
if [[ -s "${TOKEN_FILE}" ]]; then
    auth=(-H "Authorization: Bearer $(cat "${TOKEN_FILE}")")
fi

# The embeddings of the language of the model live next to it in the
# repository.
remote_dir="${target_dir}/embeddings"
listing="$(curl -fsSL ${auth[@]+"${auth[@]}"} \
    "${HF_BASE_URL}/api/models/${repo}/tree/${revision}/${remote_dir}?recursive=1" 2> /dev/null || true)"

if [[ -z "${listing}" ]]; then
    echo "ensure_tts_voices: could not read the voices of '${MODEL_ID}' from ${repo}" >&2
    exit 1
fi

remote_files="$(jq -r --arg prefix "${remote_dir}/" \
    '.[]? | select(.type == "file") | .path | select(startswith($prefix))' <<< "${listing}")"

if [[ -z "${remote_files}" ]]; then
    echo "ensure_tts_voices: the model '${MODEL_ID}' has no voices in ${repo}" >&2
    exit 1
fi

mkdir -p "${voice_dir}"

download_voice() {
    local path="$1"
    local name
    local url
    local destination

    name="$(basename "${path}")"
    destination="${voice_dir}/${name}"

    if [[ -s "${destination}" ]]; then
        return 0
    fi

    url="${HF_BASE_URL}/${repo}/resolve/${revision}/${path}"
    if ! curl -fsSL ${auth[@]+"${auth[@]}"} -o "${destination}.part.$$" "${url}"; then
        rm -f "${destination}.part.$$"
        if [[ ${#auth[@]} -gt 0 ]]; then
            # Hugging Face rejects public downloads with an invalid token, so
            # try again without it.
            if curl -fsSL -o "${destination}.part.$$" "${url}"; then
                mv "${destination}.part.$$" "${destination}"
                return 0
            fi
            rm -f "${destination}.part.$$"
        fi
        echo "ensure_tts_voices: could not download ${path}" >&2
        return 1
    fi

    mv "${destination}.part.$$" "${destination}"
    echo "ensure_tts_voices: downloaded ${path}"
    return 0
}

# The worker downloads all the voices of the language. It runs detached from
# the service, so it survives the start of the service.
if [[ "${MODE}" == "--worker" ]]; then
    # The process id of the worker goes into the lock file, so a service that
    # starts later knows that the worker is still running.
    echo $$ > "${lock_file}"
    while IFS= read -r path; do
        [[ -z "${path}" ]] && continue
        download_voice "${path}" || true
    done <<< "${remote_files}"
    # Only release the lock when it is still ours.
    if [[ "$(cat "${lock_file}" 2> /dev/null || true)" == "$$" ]]; then
        rm -f "${lock_file}"
    fi
    exit 0
fi

# The configured voice is needed right away, the bridge starts with it.
voice_path=""
while IFS= read -r path; do
    [[ "$(basename "${path}")" == "${VOICE_FILE_NAME}" ]] && voice_path="${path}"
done <<< "${remote_files}"

if [[ -z "${voice_path}" ]]; then
    echo "ensure_tts_voices: the voice '${VOICE}' is not available for the model '${MODEL_ID}'" >&2
    exit 1
fi

if ! download_voice "${voice_path}"; then
    exit 1
fi

# The other voices of the language are downloaded in the background, they are
# only needed when another voice is picked. The lock file holds the process id
# of the worker, a lock of a worker that is gone is stale and is ignored.
missing=0
while IFS= read -r path; do
    [[ -z "${path}" ]] && continue
    [[ -s "${voice_dir}/$(basename "${path}")" ]] || missing=1
done <<< "${remote_files}"

if [[ "${missing}" -eq 1 ]]; then
    worker_pid=""
    if [[ -f "${lock_file}" ]]; then
        worker_pid="$(cat "${lock_file}" 2> /dev/null || true)"
    fi

    running="false"
    if [[ "${worker_pid}" == "starting" ]]; then
        # A worker is on its way, it writes its process id into the lock file.
        age=$(( $(date +%s) - $(stat -c %Y "${lock_file}" 2> /dev/null || echo 0) ))
        [[ "${age}" -lt 60 ]] && running="true"
    elif [[ -n "${worker_pid}" ]] && kill -0 "${worker_pid}" 2> /dev/null; then
        running="true"
    fi

    if [[ "${running}" == "false" ]]; then
        # The worker runs in its own session, so it outlives the service that
        # started it. It writes its process id into the lock file.
        echo "starting" > "${lock_file}"
        setsid "${0}" "${MODEL_ID}" "${VOICE}" --worker &
        echo "ensure_tts_voices: the other voices of '${MODEL_ID}' are downloaded in the background"
    fi
fi

exit 0
