<!-- https://contributors.home-assistant.io/apps/guides/presentation/#changelog -->
## 0.9.7

- Set the defaults for German: the Qwen3 speech-to-text model, the German PocketTTS model, the language hint `de` and the voice `Anna`. Text-to-speech is enabled by default now.

## 0.9.6

- Download the voices of the text-to-speech model when they are needed. The PocketTTS models of the languages other than English do not ship a voice, so the synthesis failed with "requires a session voice".

## 0.9.6

- Download the voices of the text-to-speech model when they are needed. The PocketTTS models of the languages other than English do not ship a voice, so the synthesis failed with "requires a session voice".

## 0.9.5

- Copy the root filesystem into the image. The Supervisor does not do this, so the container had none of the services in it and nothing ran.

## 0.9.4

- Fix the app halting on start. bashio::config returns the elements of a list one after another, so the extra models are now read from the options file.
- Write the log of the server and the Wyoming bridges line by line, so it shows up right away and is not mixed up with the output of the other services.

## 0.9.3

- Download the models in the background, so a slow download no longer keeps the app from starting. The Supervisor only allows 120 seconds for an app to report that it started.
- Check the health of the app every 10 seconds instead of every 30, and start checking after 15 seconds.

## 0.9.2

- Compile the full set of speech-to-text families, so every entry in the model list works.
- Offer the models in more than one precision: q8_0, q4_k, f16, f32 and bf16.
- Add the language variants of the PocketTTS text-to-speech model in both precisions.
- Replace the placeholder images with a text logo.

## 0.9.1

- Fix the model dropdowns, the values were not separated correctly.
- Use 4 inference threads and keep one model in memory by default.
- Add extra models one by one in the form, with a family, a task and a url.
- Offer the language variants of the PocketTTS text-to-speech model.

## 0.9.0

- Initial release.
- Bundles audio.cpp v0.9.3 with the CPU backend.
- Add the Wyoming speech-to-text and text-to-speech protocol bridges.
- Add options for a Hugging Face token and for extra models from a URL.
- Add a German translation of the app configuration.
