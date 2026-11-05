#!/usr/bin/env bash
# ==============================================================================
# List the voices of a text-to-speech model family
# ==============================================================================
# Every line describes one voice of the family:
#
#   <voice>|<language>|<package id>|<model file>|<voice file>
#
# The voices of a language live next to the model of that language in the
# model repository. They are downloaded when they are used, so only their
# names are needed here.
#
# Usage: tts_family_voices.sh <family>
# ==============================================================================
set -uo pipefail

MODELS_DIR="${MODELS_DIR:-/share/audio_cpp/models}"
SPEC_DIR="${SPEC_DIR:-/app/model_specs}"
TOKEN_FILE="${TOKEN_FILE:-/root/.cache/huggingface/token}"
HF_BASE_URL="${HF_BASE_URL:-https://huggingface.co}"

FAMILY="${1:-}"

if [[ -z "${FAMILY}" ]]; then
    echo "tts_family_voices: usage: $0 <family>" >&2
    exit 2
fi

SPEC_FILE="${SPEC_DIR}/${FAMILY}.json"
if [[ ! -f "${SPEC_FILE}" ]]; then
    echo "tts_family_voices: unknown family '${FAMILY}'" >&2
    exit 1
fi

repo="$(jq -r '.package_defaults.download.repo // empty' "${SPEC_FILE}")"
revision="$(jq -r '.package_defaults.download.revision // "main"' "${SPEC_FILE}")"

auth=()
if [[ -s "${TOKEN_FILE}" ]]; then
    auth=(-H "Authorization: Bearer $(cat "${TOKEN_FILE}")")
fi

while IFS='|' read -r package target_dir gguf language; do
    [[ -n "${package}" ]] || continue

    # The names of the voices come from the model repository. Without a
    # network only the installed voices are known.
    names=""
    if [[ -n "${repo}" ]]; then
        listing="$(curl -fsSL --max-time 20 ${auth[@]+"${auth[@]}"} \
            "${HF_BASE_URL}/api/models/${repo}/tree/${revision}/${target_dir}/embeddings?recursive=1" 2> /dev/null || true)"
        names="$(jq -r --arg prefix "${target_dir}/embeddings/" '
            .[]? | select(.type == "file") | .path | select(startswith($prefix))
            | select(endswith(".safetensors"))
            | ltrimstr($prefix) | rtrimstr(".safetensors")
        ' <<< "${listing}" 2> /dev/null || true)"
    fi

    if [[ -z "${names}" ]]; then
        for embedding in "${MODELS_DIR}/${target_dir}"/embeddings/*.safetensors; do
            [[ -e "${embedding}" ]] || continue
            names="${names}$(basename "${embedding}" .safetensors)"$'\n'
        done
    fi

    while IFS= read -r name; do
        [[ -n "${name}" ]] || continue
        # The names of the voices are capitalised and the underscores become
        # spaces, so they read well in Home Assistant.
        display="${name^}"
        display="${display//_/ }"
        printf '%s|%s|%s|%s|%s\n' \
            "${display}" "${language}" "${package}" "${gguf}" \
            "${MODELS_DIR}/${target_dir}/embeddings/${name}.safetensors"
    done <<< "${names}"
done < <(/usr/local/bin/tts_family_models.sh "${FAMILY}")
