"""Tiny synthetic WAV fixtures, generated with only the Python standard
library (spec section 22). Used by demo mode and by the automated test
suite -- never real or copyrighted audio.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def generate_sine_wav(
    path: str | Path,
    *,
    seconds: float = 1.0,
    frequency_hz: float = 440.0,
    sample_rate: int = 44100,
    bit_depth: int = 16,
    channels: int = 1,
) -> Path:
    """Write a short, quiet sine-wave WAV file at ``path`` and return it.

    Deliberately tiny (a second or two) so the whole demo catalog and
    test suite stay fast and small; this is a synthesized tone, not a
    piece of music.
    """
    if bit_depth != 16:
        raise ValueError("Synthetic fixtures only support 16-bit PCM (bit_depth=16).")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_width = bit_depth // 8
    n_frames = int(seconds * sample_rate)
    max_amplitude = (2 ** (bit_depth - 1)) - 1
    volume = 0.2  # quiet by design

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(n_frames):
            sample = int(
                volume * max_amplitude * math.sin(2 * math.pi * frequency_hz * i / sample_rate)
            )
            packed = struct.pack("<h", sample)
            for _ in range(channels):
                frames.extend(packed)
        wav_file.writeframes(bytes(frames))

    return path
