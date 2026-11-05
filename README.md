# Pollonamid's Home Assistant Apps

This repository is a personal collection of Home Assistant apps (Supervisor apps) that I maintain and install on my own Home Assistant instance from the app store.

## Add this repository to Home Assistant

[![Add this repository to your Home Assistant instance.](https://my.home-assistant.io/badges/supervisor_store.svg)](https://my.home-assistant.io/redirect/supervisor_store/?repository_url=https%3A%2F%2Fgithub.com%2Fpollonamid%2Fha-apps)

Repository URL: <https://github.com/pollonamid/ha-apps>

You can add it manually via **Settings > Apps > Install app > Repositories** and pasting the URL above.

## Apps

### [Audio.cpp](./audio_cpp)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

High-performance local audio inference server: speech-to-text and text-to-speech, with CPU and Vulkan backends. It bundles [audio.cpp](https://github.com/0xShug0/audio.cpp) and the [wyoming_audiocpp](https://github.com/m-abs/wyoming_audiocpp) protocol bridges.

## Dependencies

[Renovate](https://github.com/renovatebot/renovate) keeps the dependencies up to date. It opens a pull request for the new versions of the GitHub Actions, of the base image and of the pinned versions in the `Dockerfile` (`AUDIOCPP_VERSION` for [audio.cpp](https://github.com/0xShug0/audio.cpp), `WYO_VERSION` for [wyoming_audiocpp](https://github.com/m-abs/wyoming_audiocpp)). The configuration is in `renovate.json`, the workflow that runs it is in `.github/workflows/renovate.yaml`.

A pull request from Renovate needs a version bump in `config.yaml` and a `CHANGELOG.md` entry before it can be pushed, so the image with the new dependency is built and published.

## Credits

- [audio.cpp](https://github.com/0xShug0/audio.cpp) by ShugoAI LLC (Apache-2.0) — the inference server
- [wyoming_audiocpp](https://github.com/m-abs/wyoming_audiocpp) by Morten Sjøgren (MIT) — the Wyoming protocol bridges
- [ggml](https://github.com/ggml-org/ggml) (MIT) — the tensor library audio.cpp is built on

## License

Apache-2.0 — see [LICENSE](./LICENSE).

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
