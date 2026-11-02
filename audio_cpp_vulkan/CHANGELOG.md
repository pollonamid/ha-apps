<!-- https://contributors.home-assistant.io/apps/guides/presentation/#changelog -->
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
- Bundles audio.cpp v0.9.3 with the Vulkan backend.
- Add the Wyoming speech-to-text and text-to-speech protocol bridges.
- Add options for a Hugging Face token and for extra models from a URL.
- Add a German translation of the app configuration.
