"""Audio metadata extraction using Mutagen and the standard-library
``wave`` module. Works fully without FFmpeg (spec section 11); FFmpeg only
adds loudness/true-peak numbers on top when available (see
``produceros.audio.ffmpeg``).

Metadata confidence levels (spec section 11):
- ``user_confirmed``: entered/edited by the producer -- never overwritten here.
- ``embedded``: read from file tags (ID3, RIFF INFO, Vorbis comments, ...).
- ``measured``: computed by decoding the file (duration, sample rate, ...).
- ``estimated``: derived from an external tool's own estimate (e.g. ffprobe
  container duration when the stream duration is unavailable).
"""

from __future__ import annotations

import wave
from dataclasses import dataclass, field
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".aiff", ".aif", ".mp3", ".flac", ".ogg", ".m4a"}


@dataclass
class ExtractedAudioMetadata:
    file_type: str
    is_audio: bool = False
    duration_seconds: float | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None
    channels: int | None = None
    file_size_bytes: int | None = None
    embedded_title: str | None = None
    embedded_artist: str | None = None
    embedded_album: str | None = None
    embedded_track_number: str | None = None
    warnings: list[str] = field(default_factory=list)


def _extract_wav_stdlib(path: Path) -> ExtractedAudioMetadata:
    meta = ExtractedAudioMetadata(file_type="wav", is_audio=True, file_size_bytes=path.stat().st_size)
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            meta.sample_rate = rate
            meta.channels = wav_file.getnchannels()
            meta.bit_depth = wav_file.getsampwidth() * 8
            meta.duration_seconds = round(frames / rate, 3) if rate else None
    except (wave.Error, EOFError, OSError) as exc:
        meta.warnings.append(f"Could not read WAV header: {exc}")
    return meta


def _extract_via_mutagen(path: Path, meta: ExtractedAudioMetadata | None = None) -> ExtractedAudioMetadata:
    from mutagen import File as MutagenFile  # local import: optional heavy dependency

    suffix = path.suffix.lower().lstrip(".")
    if meta is None:
        meta = ExtractedAudioMetadata(
            file_type=suffix, is_audio=suffix in {e.lstrip(".") for e in AUDIO_EXTENSIONS}
        )
        meta.file_size_bytes = path.stat().st_size

    try:
        mutagen_file = MutagenFile(str(path), easy=True)
    except Exception as exc:  # pragma: no cover - mutagen raises many types
        meta.warnings.append(f"Mutagen could not parse file: {exc}")
        return meta

    if mutagen_file is None:
        meta.warnings.append("Mutagen did not recognize this file as audio.")
        return meta

    meta.is_audio = True
    info = getattr(mutagen_file, "info", None)
    if info is not None:
        meta.duration_seconds = round(getattr(info, "length", 0.0), 3) or meta.duration_seconds
        meta.sample_rate = getattr(info, "sample_rate", None) or meta.sample_rate
        meta.channels = getattr(info, "channels", None) or meta.channels
        bits = getattr(info, "bits_per_sample", None)
        if bits:
            meta.bit_depth = bits

    tags = mutagen_file.tags or {}

    def first(*keys: str) -> str | None:
        for key in keys:
            value = tags.get(key)
            if value:
                return str(value[0]) if isinstance(value, list) else str(value)
        return None

    meta.embedded_title = first("title") or meta.embedded_title
    meta.embedded_artist = first("artist") or meta.embedded_artist
    meta.embedded_album = first("album") or meta.embedded_album
    meta.embedded_track_number = first("tracknumber") or meta.embedded_track_number
    return meta


def extract_metadata(path: str | Path) -> ExtractedAudioMetadata:
    """Best-effort metadata extraction for any scanned/registered file.

    Non-audio files (images, PDFs, project files, etc.) return a minimal
    result with ``is_audio=False`` rather than raising.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if not path.exists():
        return ExtractedAudioMetadata(
            file_type=suffix.lstrip("."), warnings=[f"File not found: {path}"]
        )

    if suffix == ".wav":
        meta = _extract_wav_stdlib(path)
        try:
            meta = _extract_via_mutagen(path, meta)
        except ImportError:
            meta.warnings.append("Mutagen not installed; used stdlib wave only.")
        return meta

    if suffix in AUDIO_EXTENSIONS:
        try:
            return _extract_via_mutagen(path)
        except ImportError:
            return ExtractedAudioMetadata(
                file_type=suffix.lstrip("."),
                file_size_bytes=path.stat().st_size,
                warnings=["Mutagen is not installed; audio metadata unavailable."],
            )

    return ExtractedAudioMetadata(
        file_type=suffix.lstrip("."),
        is_audio=False,
        file_size_bytes=path.stat().st_size if path.exists() else None,
    )
