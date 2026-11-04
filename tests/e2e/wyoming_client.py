"""Client for the Wyoming TTS and ASR endpoints of the audio_cpp addon.

The bridges of the addon are not standard Wyoming implementations: the TTS
bridge answers a ``Synthesize`` request with ``AudioStart``, a number of
``AudioChunk`` events and ``AudioStop``, and the ASR bridge serves exactly one
utterance per connection and answers it with a single ``Transcript`` event.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import async_read_event, async_write_event
from wyoming.tts import Synthesize, SynthesizeVoice

DEFAULT_TIMEOUT = 300.0


@dataclass(frozen=True)
class AudioFormat:
    """Sample rate, sample width and channel count of raw PCM audio."""

    rate: int
    width: int
    channels: int


@dataclass(frozen=True)
class SynthesizedAudio:
    """Raw PCM audio together with the format it was produced in."""

    pcm: bytes
    audio_format: AudioFormat

    def to_wav(self) -> bytes:
        """Wrap the raw PCM audio in a WAV container."""
        import wave
        import io

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(self.audio_format.channels)
            wav.setsampwidth(self.audio_format.width)
            wav.setframerate(self.audio_format.rate)
            wav.writeframes(self.pcm)
        return buffer.getvalue()


async def synthesize(
    host: str,
    port: int,
    text: str,
    voice: str = "Alba",
    timeout: float = DEFAULT_TIMEOUT,
) -> SynthesizedAudio:
    """Synthesize ``text`` and return the raw PCM audio of the answer."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        request = Synthesize(text=text, voice=SynthesizeVoice(name=voice)).event()
        await async_write_event(request, writer)

        audio_format: AudioFormat | None = None
        chunks: list[bytes] = []
        while True:
            event = await asyncio.wait_for(async_read_event(reader), timeout)
            if event is None:
                break
            if AudioStart.is_type(event.type):
                start = AudioStart.from_event(event)
                audio_format = AudioFormat(start.rate, start.width, start.channels)
            elif AudioChunk.is_type(event.type):
                chunks.append(AudioChunk.from_event(event).audio)
            elif AudioStop.is_type(event.type):
                break
            elif Error.is_type(event.type):
                raise RuntimeError(
                    f"The TTS bridge failed: {Error.from_event(event).text}"
                )

        if audio_format is None:
            raise RuntimeError(f"The TTS bridge sent no audio for {text!r}")
        if not chunks:
            raise RuntimeError(f"The TTS bridge sent an empty audio for {text!r}")

        return SynthesizedAudio(pcm=b"".join(chunks), audio_format=audio_format)
    finally:
        writer.close()
        await writer.wait_closed()


async def transcribe(
    host: str,
    port: int,
    audio: SynthesizedAudio,
    language: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Transcribe the given audio and return the transcript."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        fmt = audio.audio_format
        events = [
            Transcribe(language=language).event(),
            AudioStart(rate=fmt.rate, width=fmt.width, channels=fmt.channels).event(),
            AudioChunk(
                audio=audio.pcm,
                rate=fmt.rate,
                width=fmt.width,
                channels=fmt.channels,
            ).event(),
            AudioStop().event(),
        ]
        for event in events:
            await async_write_event(event, writer)

        while True:
            event = await asyncio.wait_for(async_read_event(reader), timeout)
            if event is None:
                raise RuntimeError("The ASR bridge closed the connection without a transcript")
            if Transcript.is_type(event.type):
                return Transcript.from_event(event).text
            if Error.is_type(event.type):
                raise RuntimeError(f"The ASR bridge failed: {Error.from_event(event).text}")
    finally:
        writer.close()
        await writer.wait_closed()
