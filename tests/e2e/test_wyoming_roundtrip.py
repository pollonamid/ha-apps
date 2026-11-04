"""End-to-end test of the Wyoming TTS and ASR endpoints of the addon.

The addon synthesizes a sentence with the Wyoming TTS endpoint and transcribes
the generated audio again with the Wyoming ASR endpoint. The transcript has to
contain the spoken text.
"""

from __future__ import annotations

import asyncio
import string
import time
from pathlib import Path

import pytest

import conftest
import wyoming_client

MIN_TOKEN_RATIO = 0.5
TRANSCRIBE_ATTEMPTS = 3


def tokenize(text: str) -> list[str]:
    """Split a text into comparable lower case words."""
    cleaned = text.lower().translate(str.maketrans("", "", string.punctuation))
    return cleaned.split()


def transcribe_with_retry(
    addon: conftest.Addon,
    audio: wyoming_client.SynthesizedAudio,
    scenario: conftest.Scenario,
    attempts: int = TRANSCRIBE_ATTEMPTS,
) -> str:
    """Transcribe the audio, retrying while the model is still loading."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return asyncio.run(
                wyoming_client.transcribe(
                    "127.0.0.1",
                    addon.asr_port,
                    audio,
                    scenario.asr_language,
                )
            )
        except Exception as exc:  # noqa: BLE001 - the reason is reported
            last_error = exc
            print(f"\n[test] transcription attempt {attempt} failed: {exc}")
            time.sleep(5)
    raise AssertionError(f"The ASR bridge did not transcribe the audio: {last_error}")


def test_wyoming_roundtrip(
    scenario: conftest.Scenario,
    addon: conftest.Addon,
    tmp_path: Path,
) -> None:
    """The transcript of the synthesized audio has to contain the spoken text."""
    if scenario.asr_language == "auto":
        pytest.skip("The round trip needs a fixed language for the transcription")

    audio = asyncio.run(
        wyoming_client.synthesize(
            "127.0.0.1",
            addon.tts_port,
            scenario.text,
            voice=conftest.TTS_VOICE,
        )
    )
    assert audio.pcm, "The TTS bridge returned no audio"

    wav_path = tmp_path / f"{scenario.name}.wav"
    wav_path.write_bytes(audio.to_wav())
    print(
        f"\n[test] {scenario.name}: {len(audio.pcm)} bytes of PCM "
        f"at {audio.audio_format.rate} Hz, {audio.audio_format.width} byte(s), "
        f"{audio.audio_format.channels} channel(s), saved to {wav_path}"
    )

    transcript = transcribe_with_retry(addon, audio, scenario)
    print(f"[test] {scenario.name}: transcript: {transcript!r}")

    reference_tokens = tokenize(scenario.text)
    transcript_tokens = tokenize(transcript)
    assert transcript_tokens, f"The transcript is empty, audio: {wav_path}"

    matched = set(reference_tokens) & set(transcript_tokens)
    ratio = len(matched) / len(reference_tokens)
    assert ratio >= MIN_TOKEN_RATIO, (
        f"The transcript does not contain the spoken text.\n"
        f"Reference: {scenario.text!r}\n"
        f"Transcript: {transcript!r}\n"
        f"Matched tokens: {sorted(matched)} of {sorted(set(reference_tokens))}\n"
        f"Audio: {wav_path}"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
