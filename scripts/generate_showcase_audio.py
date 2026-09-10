"""Original, deterministic instrumental demos. No samples, services or user files.

All voices are synthesized from oscillators/noise using the standard library.
Fictional artist names identify examples, never real producer submissions.
"""

from __future__ import annotations

import array
import io
import math
import random
import sys
import wave
from pathlib import Path
from typing import TypedDict


class DemoTrack(TypedDict):
    id: str
    artist: str
    title: str
    genre: str
    bpm: int
    key: str
    root: int
    seed: int
    question: str


DEMO_TRACKS: tuple[DemoTrack, ...] = (
    {
        "id": "hoodie-monstah-night-shift",
        "artist": "Hoodie Monstah",
        "title": "Night Shift",
        "genre": "Dark trap",
        "bpm": 140,
        "key": "F minor",
        "root": 29,
        "seed": 41,
        "question": "Would you keep the sparse opening, or bring the hats in sooner?",
    },
    {
        "id": "deid-gravic-side-street",
        "artist": "Deid Gravic",
        "title": "Side Street",
        "genre": "Laid-back rap",
        "bpm": 92,
        "key": "D minor",
        "root": 38,
        "seed": 82,
        "question": "Does the space between the keys leave enough room for a vocal?",
    },
    {
        "id": "lowkey-circuit-blue-hour",
        "artist": "Lowkey Circuit",
        "title": "Blue Hour",
        "genre": "Melodic trap",
        "bpm": 128,
        "key": "A minor",
        "root": 33,
        "seed": 123,
        "question": "Does the melody need a variation when the drums return?",
    },
)


def synthesize_demo(track: DemoTrack) -> bytes:
    rate = 22050
    beat = 60 / track["bpm"]
    bars = 16 if track["bpm"] == 92 else 20
    total = round(bars * 4 * beat * rate)
    mix = [0.0] * total
    rng = random.Random(track["seed"])
    rap = track["bpm"] == 92
    melodic = track["bpm"] == 128

    def voice(start: float, length: float, kind: str, gain: float, midi: int = 48) -> None:
        offset = round(start * rate)
        count = min(round(length * rate), total - offset)
        frequency = 440 * 2 ** ((midi - 69) / 12)
        previous_noise = 0.0
        for index in range(max(0, count)):
            t = index / rate
            tail = min(1, (count - index) / (rate * 0.025))
            if kind == "kick":
                phase = 2 * math.pi * (47 * t + 100 * 0.022 * (1 - math.exp(-t / 0.022)))
                value = math.sin(phase) * math.exp(-t * 11)
                value += rng.uniform(-1, 1) * math.exp(-t * 240) * 0.13
            elif kind in {"hat", "open_hat", "snare"}:
                noise = rng.uniform(-1, 1)
                high = noise - previous_noise * 0.8
                previous_noise = noise
                decay = 74 if kind == "hat" else 18 if kind == "open_hat" else 22
                value = high * math.exp(-t * decay)
                if kind == "snare":
                    value = (noise * 0.68 + math.sin(2 * math.pi * 185 * t) * 0.32) * math.exp(
                        -t * 23
                    )
                    # Tiny noise bursts give the snare a clap-like edge.
                    for delay in (0.011, 0.022):
                        if t >= delay:
                            value += noise * 0.18 * math.exp(-(t - delay) * 65)
            elif kind == "bass":
                # Softly saturated sub with a short pitch drop and a decaying harmonic.
                phase = (
                    2 * math.pi * (frequency * t + frequency * 0.018 * (1 - math.exp(-t / 0.018)))
                )
                value = math.tanh(1.65 * (math.sin(phase) + 0.14 * math.sin(2 * phase)))
                value *= min(1, t / 0.008) * math.exp(-t * 1.3)
            else:
                phase = 2 * math.pi * frequency * t
                attack = min(1, t / 0.012)
                if kind == "keys":
                    value = (
                        math.sin(phase)
                        + 0.23 * math.sin(2 * phase) * math.exp(-t * 5)
                        + 0.08 * math.sin(3 * phase)
                    ) * math.exp(-t * 2.5)
                else:
                    value = (
                        math.sin(phase + 1.5 * math.sin(phase * 2) * math.exp(-t * 6))
                        + 0.16 * math.sin(phase * 1.003)
                    ) * math.exp(-t * 3.4)
                value *= attack
            mix[offset + index] += gain * value * tail

    progression = (0, -3, -5, -2) if not melodic else (0, -5, -3, -7)
    for bar in range(bars):
        root = track["root"] + progression[(bar // 2) % 4]
        start = bar * 4 * beat
        sparse = bar < 2 or bar in (8, 9)
        # Minor/dorian color, with an open voicing above the bass.
        chord = (root + 24, root + 31, root + 39, root + 43)
        if rap:
            for when in (0, 1.65, 3.1):
                for note in chord:
                    voice(start + when * beat, beat * 1.6, "keys", 0.065, note)
        else:
            melody = (12, 19, 15, 22, 19, 15, 10, 15) if melodic else (24, 19, 15, 12)
            for step, interval in enumerate(melody):
                when = step * (0.5 if melodic else 1) * beat
                level = 0.12 if melodic else 0.105
                voice(start + when, beat * 1.4, "bell", level, root + interval + 12)
                voice(
                    start + when + beat * 0.75,
                    beat * 1.1,
                    "bell",
                    level * 0.18,
                    root + interval + 12,
                )
            if melodic:
                for note in chord[:3]:
                    voice(start, beat * 3, "keys", 0.045, note)
        if bar == bars - 1:
            continue
        kicks: tuple[float, ...] = (0, 1.5, 2.75) if rap else (0, 1.75, 3.25)
        if bar % 4 == 3:
            kicks = (*kicks, 3.75)
        for when in kicks[:1] if sparse else kicks:
            voice(start + when * beat, 0.48, "kick", 0.60)
            voice(start + when * beat, beat * (1.3 if when == 0 else 0.6), "bass", 0.29, root)
        for when in (1, 3) if rap else (2,):
            voice(start + when * beat, 0.25, "snare", 0.23 if rap else 0.27)
        if sparse:
            continue
        for step in range(8):
            # Deliberate swing in the rap beat; varying velocities in every beat.
            when = step * 0.5 + (0.075 if rap and step % 2 else 0)
            voice(start + when * beat, 0.09, "hat", 0.045 if step % 2 else 0.065)
        voice(start + 3.5 * beat, 0.25, "open_hat", 0.045)
        if not rap and bar % 2 == 1:
            for step in range(4):
                voice(start + (3.5 + step / 8) * beat, 0.07, "hat", 0.04 + step * 0.006)
    peak = max(abs(value) for value in mix)
    pcm = array.array("h")
    for index, value in enumerate(mix):
        fade = min(1, index / (rate * 0.012), (total - index - 1) / (rate * 0.25))
        pcm.append(round(value / max(peak, 1) * 29000 * fade))
    if sys.byteorder != "little":
        pcm.byteswap()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())
    return buffer.getvalue()


def generate_demos(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    files = []
    for track in DEMO_TRACKS:
        destination = directory / f"{track['id']}.wav"
        content = synthesize_demo(track)
        if destination.exists():
            if destination.read_bytes() != content:
                raise ValueError(f"Refusing to overwrite existing demo audio: {destination.name}")
        else:
            with destination.open("xb") as output:
                output.write(content)
        files.append(destination)
    return files
