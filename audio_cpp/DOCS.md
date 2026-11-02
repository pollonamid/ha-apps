# Audio.cpp

## What it does

- Runs the [audio.cpp](https://github.com/0xShug0/audio.cpp) inference server locally inside Home Assistant.
- Speaks an OpenAI-compatible API: `POST /v1/audio/transcriptions` (multipart `file` + `model`), plus `GET /health`, `GET /v1/models`, `POST /v1/audio/speech`.
- The embedded web interface is reachable from the sidebar of Home Assistant (ingress).
- Everything runs locally. Only the model download needs internet access.

## Options

| Option | Default | Description |
| --- | --- | --- |
| `model` | `citrinet_asr_q8_0` | The speech-to-text model to use. It is downloaded on the first start. |
| `backend` | `cpu` | The inference backend to use. This build ships the CPU backend. |
| `threads` | `4` | The number of CPU threads used for inference. |
| `max_loaded_models` | `1` | How many models may stay loaded in memory at the same time. |
| `auto_install_model` | `true` | Download the selected model automatically when it is missing. |
| `enable_tts` | `false` | Enable the Wyoming text-to-speech bridge and the text-to-speech model. |
| `tts_model` | `pocket_tts_english_q8_0` | The text-to-speech model to use. PocketTTS is available in several languages, every one of them is around 125 MB. It is downloaded on the first start when text-to-speech is enabled. |
| `asr_language` | `en` | The language hint sent with the transcription request. Use `auto` to let the model decide. |
| `tts_voice` | `Alba` | The name of the voice used for speech synthesis. |
| `hf_token` | (empty) | A Hugging Face access token. It is needed for restricted or gated repositories and is used for every download. |
| `extra_models` | (empty) | Additional models from a Hugging Face url. Use **Add item** to add more than one. |

## Models

The selected model is downloaded on the first start into `/share/audio_cpp/models` and kept there across restarts and updates. Nothing is downloaded again while the file is present.

The download runs in the background, so the app is ready right away. The model is loaded when it is used for the first time, which takes a moment longer while the download is still running.

Every model that this build can load is listed in the `model` and `tts_model` options. The tables below show how large the download is.

### Speech to text

| Model id | Approx. download size |
| --- | --- |
| `citrinet_asr_q8_0` | 39 MB |
| `moonshine_streaming_tiny_q8_0` | 58 MB |
| `owsm_v4_base_102m_q8_0` | 113 MB |
| `kroko_asr_community_q8_0` | 160 MB |
| `whistle_asr_f32` | 211 MB |
| `canary_180m_flash_q8_0` | 238 MB |
| `sensevoice_small_q8` | 242 MB |
| `niagara_19m_f32` | 244 MB |
| `owsm_v4_small_370m_q4_k` | 283 MB |
| `moonshine_streaming_small_q8_0` | 287 MB |
| `moonshine_streaming_medium_q8_0` | 301 MB |
| `owsm_v4_base_102m_f32` | 316 MB |
| `niagara_38m_f32` | 407 MB |
| `owsm_v4_small_370m_q8_0` | 412 MB |
| `granite5asr_q8_0` | 481 MB |
| `owsm_v4_medium_1b_q4_k` | 687 MB |
| `canary_180m_flash_f32` | 723 MB |
| `parakeet_tdt_q8_0` | 873 MB |
| `nemotron_asr_q8_0` | 888 MB |
| `fun_asr_nano_2512_q8_0` | 997 MB |
| `qwen3_asr_0_6b_q8_0` | 1098 MB |
| `owsm_v4_medium_1b_q8_0` | 1107 MB |
| `parakeet_tdt_f16` | 1197 MB |
| `nemotron_asr_f16` | 1219 MB |
| `owsm_v4_small_370m_f32` | 1264 MB |
| `hviske_asr_v6_q8_0` | 1574 MB |
| `fun_asr_nano_2512_f16` | 1598 MB |
| `qwen3_asr_0_6b_f16` | 1794 MB |
| `hviske_asr_q8_0` | 2323 MB |
| `qwen3_asr_1_7b_q8_0` | 2358 MB |
| `qwencleo_asr_q8_0` | 2363 MB |
| `hviske_asr_v6_bf16` | 2674 MB |
| `owsm_v4_medium_1b_f32` | 3705 MB |
| `qwen3_asr_1_7b_f16` | 3898 MB |
| `qwencleo_asr_f16` | 3903 MB |

### Text to speech

| Model id | Approx. download size |
| --- | --- |
| `pocket_tts_german_q8_0` | 122 MB |
| `pocket_tts_italian_q8_0` | 122 MB |
| `pocket_tts_portuguese_q8_0` | 122 MB |
| `pocket_tts_spanish_q8_0` | 122 MB |
| `pocket_tts_english_q8_0` | 128 MB |
| `pocket_tts_french_q8_0` | 128 MB |
| `pocket_tts_german_bf16` | 209 MB |
| `pocket_tts_italian_bf16` | 209 MB |
| `pocket_tts_portuguese_bf16` | 209 MB |
| `pocket_tts_spanish_bf16` | 209 MB |
| `pocket_tts_english_bf16` | 215 MB |
| `pocket_tts_french_bf16` | 215 MB |

Most models come in more than one precision. `q8_0` is the smallest and fastest, `f16`, `f32` and `bf16` keep more of the original weights and are usually more accurate, and `q4_k` is the smallest of all at the cost of accuracy. A bigger model needs more memory and takes longer.

Citrine is English only. Whisper-style models from llama.cpp or whisper.cpp cannot be used, audio.cpp uses its own GGUF layout.

## Adding models

There are three ways to get a model onto the app.

**From the built-in list.** The `model` and `tts_model` options pick a model from the list of the models that audio.cpp publishes. The model is downloaded on the first start into `/share/audio_cpp/models` and stays there over restarts and updates.

**From the web interface.** The app has a web interface with a model manager. It is reachable from the app page through **Open Web UI**, and it is served through the Home Assistant ingress, so it needs no separate login. There you can install models from the same built-in list, upload voice files and delete models. The models it installs are stored in `/share/audio_cpp/models` as well.

**By URL.** The `extra_models` option adds models from a Hugging Face url. Use **Add item** in the form for every model you want, and fill in the three fields:

- `family` is the audio.cpp model family. Only the families that are compiled into this build can be loaded. They are the families of the models in the built-in list.
- `task` is what the model does, for example `asr` for speech to text or `tts` for text to speech.
- `url` points to a `.gguf` file on Hugging Face. A link to the repository works too when it holds exactly one `.gguf` file.

An entry looks like this:

    family: citrinet_asr
    task: asr
    url: https://huggingface.co/owner/repository/resolve/main/model-q8_0.gguf

The models are downloaded on the next start of the app and then show up in the web interface and in the API. The id of a model is its file name without the extension, and you use that id as the `model` value in a request.

## Hugging Face token

Some repositories on Hugging Face are gated and need a token. Put the token in the `hf_token` option. It is stored in the app and used for every download, including the models that the web interface installs. The token is never sent to Home Assistant.

If the token is wrong, Hugging Face refuses even public downloads. The app then retries the download without the token, so the built-in models still work.

## Using the API

Transcribe an audio file:

```
curl -X POST http://<home-assistant>:8099/v1/audio/transcriptions \
  -F model=citrinet_asr_q8_0 \
  -F language=en \
  -F file=@speech.wav
```

The audio must be 16 kHz mono WAV.

The port is off by default. Enable it in the app configuration under Network before you can reach the API from outside of Home Assistant.

## Wyoming protocol

The app ships the two Wyoming protocol bridges from [wyoming_audiocpp](https://github.com/m-abs/wyoming_audiocpp) so Home Assistant can use it directly as a voice assistant provider. The bridges are part of the same container and talk to the local audio.cpp server.

| Service | Port inside the container | Purpose |
| --- | --- | --- |
| Wyoming speech-to-text | 11301/tcp | Turns speech into text |
| Wyoming text-to-speech | 11201/tcp | Turns text into speech |

### Connecting it to Home Assistant

1. Open the app configuration and go to the **Network** section.
2. Enable the port **11301/tcp** for speech-to-text and, if you enabled text-to-speech, also **11201/tcp**. The published host port can be changed to any free port on your machine.
3. Restart the app.
4. In Home Assistant, add an integration of type **Wyoming** and enter the URI `wyoming://<your-home-assistant-address>:<the-port-you-published>`, for example `wyoming://192.168.1.10:11301`.

Notes:

- The bridges do not announce themselves over mDNS, because the Home Assistant Supervisor app network does not forward multicast. Use the explicit URI.
- The Wyoming speech-to-text bridge forwards the transcription request to audio.cpp and returns the text. It has a fixed 15 second timeout, so a very large model on a slow CPU can time out.
- The Wyoming text-to-speech bridge is idle until you enable text-to-speech in the options.
- The Wyoming protocol bridge does not return word-level timestamps.

## GPU support

This build uses the CPU backend. It runs on any machine that Home Assistant supports, and no special hardware is needed.

For GPU acceleration there is a separate **Audio.cpp Vulkan** app in this repository. It uses the same models and the same API, and only differs in the build and in the GPU access it requests.

## Troubleshooting

- The model download fails: check the internet connection of the instance and the app log.
- The first start takes a long time: the model is downloaded and loaded on demand.
- Out of memory: pick a smaller model or lower `max_loaded_models`.
- The web interface does not open: check the app log for the port.

## Credits

- audio.cpp by ShugoAI LLC — https://github.com/0xShug0/audio.cpp (Apache-2.0)
- ggml, the tensor library it is built on — https://github.com/ggml-org/ggml (MIT)
- wyoming_audiocpp by Morten Sjøgren — https://github.com/m-abs/wyoming_audiocpp (MIT)
