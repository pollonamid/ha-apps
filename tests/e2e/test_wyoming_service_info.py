"""End-to-end test of the service info of the Wyoming endpoints.

Home Assistant reads the info of a Wyoming service to decide whether it can
use it and for which languages. The speech-to-text service has to report the
language of the model, and the text-to-speech service the languages of its
voices. A service that reports the wrong language is greyed out in the voice
assistant settings.
"""

from __future__ import annotations

import asyncio

import pytest

import conftest
import wyoming_client


def test_speech_to_text_reports_the_language(
    scenario: conftest.Scenario,
    addon: conftest.Addon,
) -> None:
    """The speech-to-text service has to report the language of the model."""
    info = asyncio.run(wyoming_client.describe("127.0.0.1", addon.asr_port))

    assert info.asr, "The service reports no speech-to-text program"
    models = [model for program in info.asr for model in program.models]
    assert models, "The service reports no speech-to-text model"

    languages = {
        language for model in models if model.installed for language in model.languages
    }
    assert languages, "The service reports no language"

    assert scenario.asr_language in languages, (
        f"The service reports the languages {sorted(languages)}, "
        f"but the model speaks {scenario.asr_language!r}."
    )

    # The model speaks more than one language, the service has to report all
    # of them, otherwise Home Assistant greys the engine out for most of the
    # pipelines.
    assert len(languages) > 1, (
        f"The service reports only the languages {sorted(languages)}, "
        "but the model speaks many more."
    )


def test_text_to_speech_offers_the_voices(
    scenario: conftest.Scenario,
    addon: conftest.Addon,
) -> None:
    """The text-to-speech service has to offer the voices with their language."""
    info = asyncio.run(wyoming_client.describe("127.0.0.1", addon.tts_port))

    assert info.tts, "The service reports no text-to-speech program"
    voices = [voice for program in info.tts for voice in program.voices]
    assert voices, "The service reports no voice"

    languages = {
        language for voice in voices if voice.installed for language in voice.languages
    }
    assert scenario.tts_language in languages, (
        f"The service reports the languages {sorted(languages)}, "
        f"but the voice speaks {scenario.tts_language!r}."
    )

    # The voice is picked in Home Assistant, so all the voices of the family
    # have to be offered.
    assert len(voices) > 1, (
        f"The service offers only the voices {[voice.name for voice in voices]}."
    )

    # The family speaks several languages, every one of them has to be
    # offered.
    assert len(languages) > 1, (
        f"The service reports the languages {sorted(languages)}, "
        "but the family speaks several."
    )

    names = [voice.name for voice in voices]
    assert len(names) == len(set(names)), f"The voice names are not unique: {names}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
