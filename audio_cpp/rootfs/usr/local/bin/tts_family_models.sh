#!/usr/bin/env bash
# ==============================================================================
# List the models of a text-to-speech model family
# ==============================================================================
# Every line describes one model of the family:
#
#   <package id>|<target directory>|<model file>|<language>
#
# One model per language, the one with the smallest precision. The models that
# are not on the disk are downloaded when they are used.
#
# Usage: tts_family_models.sh <family>
# ==============================================================================
set -uo pipefail

MODELS_DIR="${MODELS_DIR:-/share/audio_cpp/models}"
SPEC_DIR="${SPEC_DIR:-/app/model_specs}"

FAMILY="${1:-}"

if [[ -z "${FAMILY}" ]]; then
    echo "tts_family_models: usage: $0 <family>" >&2
    exit 2
fi

SPEC_FILE="${SPEC_DIR}/${FAMILY}.json"
if [[ ! -f "${SPEC_FILE}" ]]; then
    echo "tts_family_models: unknown family '${FAMILY}'" >&2
    exit 1
fi

# The name of the language of a model.
language_of_model() {
    case "$1" in
        english) echo "en" ;;
        german) echo "de" ;;
        french) echo "fr" ;;
        italian) echo "it" ;;
        portuguese) echo "pt" ;;
        spanish) echo "es" ;;
        *) echo "" ;;
    esac
}

# Every package of the family with its language and its precision.
packages=""
while IFS= read -r package; do
    [[ -n "${package}" ]] || continue

    target_dir="$(jq -r --arg id "${package}" \
        '.packages[] | select(.id == $id) | .target_directory' "${SPEC_FILE}")"
    model_name="$(basename "${target_dir}")"
    language="$(language_of_model "${model_name}")"
    [[ -n "${language}" ]] || continue

    precision="$(jq -r --arg id "${package}" \
        '.packages[] | select(.id == $id) | .precision // ""' "${SPEC_FILE}")"
    packages="${packages}${language}|${package}|${precision}|${target_dir}"$'\n'
done < <(jq -r '
    .packages[]?
    | select(.target_directory | test("^[A-Za-z0-9_-]+/[a-z]+$"))
    | . as $package
    | (.target_directory | split("/") | last) as $name
    | select($name | test("^[a-z]+$"))
    | .id
' "${SPEC_FILE}")

# One model per language, the q8_0 files are the smallest.
declare -A chosen=()
declare -A dirs=()
declare -a order=()
while IFS='|' read -r language package precision target_dir; do
    [[ -n "${language}" ]] || continue
    if [[ -z "${chosen[${language}]:-}" ]]; then
        chosen[${language}]="${package}"
        dirs[${language}]="${target_dir}"
        order+=("${language}")
    elif [[ "${precision}" == "q8_0" ]]; then
        chosen[${language}]="${package}"
        dirs[${language}]="${target_dir}"
    fi
done <<< "${packages}"

for language in "${order[@]}"; do
    package="${chosen[${language}]}"
    target_dir="${dirs[${language}]}"

    gguf="$(jq -r --arg id "${package}" \
        '.packages[] | select(.id == $id) | .files[] | select(endswith(".gguf"))' "${SPEC_FILE}" | head -1)"
    [[ -n "${gguf}" ]] || continue

    printf '%s|%s|%s|%s\n' \
        "${package}" "${target_dir}" "${MODELS_DIR}/${gguf}" "${language}"
done
