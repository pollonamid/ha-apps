# End-to-end tests for the audio_cpp addon

These tests run the real addon image in Docker and check that the Wyoming TTS
and ASR endpoints work together: a sentence is synthesized over the Wyoming
TTS endpoint and the generated audio is transcribed again over the Wyoming ASR
endpoint. The transcript has to contain the spoken text.

## Requirements

* Docker with the daemon running
* Python 3.10 or newer
* Network access, the addon image downloads the models on the first run

## Setup

```bash
uv venv tests/e2e/.cache/venv
uv pip install --python tests/e2e/.cache/venv/bin/python -r tests/e2e/requirements.txt
```

A plain virtualenv works as well:

```bash
python3 -m venv tests/e2e/.cache/venv
tests/e2e/.cache/venv/bin/pip install -r tests/e2e/requirements.txt
```

## Running the tests

```bash
tests/e2e/run.sh
```

The script creates the virtual environment on the first run and then calls
pytest. It takes the same arguments as pytest, so a single scenario is
selected with `-k`:

```bash
tests/e2e/run.sh -k english
```

The tests can also be called directly:

```bash
tests/e2e/.cache/venv/bin/python -m pytest tests/e2e -v
```

The image under test is built from `audio_cpp/Dockerfile`. To use an existing
image instead, set `E2E_IMAGE`:

```bash
E2E_IMAGE=ghcr.io/pollonamid/audio-cpp:latest \
    tests/e2e/run.sh
```

## How it works

The addon reads its options with `bashio`, which asks the Home Assistant
Supervisor for `/addons/self/options/config`. Outside of Home Assistant there
is no Supervisor, so the tests start `mock_supervisor.py` on the host. It
answers that request with the content of an `options.json` file and re-reads
the file on every request, so the options can be changed between scenarios.
The container is pointed at it with `--add-host supervisor:host-gateway` and
`SUPERVISOR_API=http://supervisor:<port>`.

Every scenario gets its own container with its own host ports. The test waits
until the HTTP API answers on `/health`, until both Wyoming ports accept
connections and until the models are on disk in the shared `/share` directory.

The models are large, so the first run downloads them. They are stored in
`tests/e2e/.cache/share` and reused by the following runs. The container
writes them as `root`, so the directory cannot be removed by a normal user;
remove it with a helper container if you want to start over:

```bash
docker run --rm -v "$PWD/tests/e2e/.cache/share:/share" alpine rm -rf /share/audio_cpp
```

## Scenarios

| Scenario  | TTS model                 | ASR language | Text                                     |
| --------- | ------------------------- | ------------ | ---------------------------------------- |
| `english` | `pocket_tts_english_q8_0` | `en`         | The quick brown fox jumps over the lazy dog. |
| `german`  | `pocket_tts_german_q8_0`  | `de`         | Das ist ein Test der Spracherkennung.    |

The comparison is tolerant: the reference and the transcript are lower cased,
stripped of punctuation and split into words. At least half of the reference
words have to be part of the transcript, and the transcript must not be empty.
The generated WAV file is written into the pytest temporary directory, its path
is part of the failure message.

The test also waits for the voice of the text-to-speech model. The app
downloads the voices of the language of the model when they are missing, the
PocketTTS models of the languages other than English do not ship one.
