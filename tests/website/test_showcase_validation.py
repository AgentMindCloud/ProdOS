"""Publication boundaries for the static curated showcase; no real submissions."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.build_website import clip_platform, render_showcase
from scripts.generate_showcase_audio import generate_demos

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (ROOT / "website/showcase.html").read_text(encoding="utf-8")


@pytest.fixture
def entry():
    return {
        "id": "test-clip",
        "producer": "Test producer",
        "title": "Test clip",
        "url": "https://soundcloud.com/test-producer/test-clip",
        "feedback_question": "How does the opening feel?",
        "duration_seconds": 45,
        "publication_approved": True,
        "producer_permission_confirmed": True,
    }


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "http://soundcloud.com/a/b",
        "https://soundcloud.com.evil.example/a/b",
        "https://soundcloud.com@evil.example/a/b",
        "https://user:password@soundcloud.com/a/b",
        "https://soundcloud.com:443/a/b",
        "https://127.0.0.1/private.wav",
        "https://soundcloud.com/a/b?secret_token=private",
        "https://soundcloud.com/a/b#private",
        "https://soundcloud.com/a/b\n",
        "https://youtube.com/redirect?q=https://evil.example",
        "https://youtube.com/watch?v=abcdefghijk&v=lmnopqrstuv",
        "https://artist.bandcamp.com.evil.example/track/clip",
        "https://open.spotify.com/playlist/123",
    ],
)
def test_only_direct_public_music_page_urls_are_accepted(url):
    with pytest.raises(ValueError):
        clip_platform(url)


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://soundcloud.com/test-producer/test-clip", "SoundCloud"),
        ("https://test-producer.bandcamp.com/track/test-clip", "Bandcamp"),
        ("https://open.spotify.com/track/0123456789ABCDEFGHIJKL", "Spotify"),
        ("https://www.youtube.com/watch?v=abcdefghijk", "YouTube"),
        ("https://youtu.be/abcdefghijk", "YouTube"),
    ],
)
def test_supported_public_music_page_urls(url, platform):
    assert clip_platform(url) == platform


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("publication_approved", False),
        ("producer_permission_confirmed", "true"),
        ("producer_permission_confirmed", False),
        ("duration_seconds", 120),
        ("duration_seconds", True),
        ("id", "../private"),
        ("bpm", "unknown"),
        ("email", "private@example.invalid"),
    ],
)
def test_unapproved_invalid_or_private_intake_data_cannot_build(entry, field, value):
    entry[field] = value
    with pytest.raises(ValueError):
        render_showcase(TEMPLATE, {"entries": [entry]})


def test_duplicate_producers_and_overfilled_pilot_refused(entry):
    with pytest.raises(ValueError, match="one clip"):
        render_showcase(TEMPLATE, {"entries": [entry, {**entry, "id": "second-clip"}]})
    with pytest.raises(ValueError, match="at most 10"):
        render_showcase(TEMPLATE, {"entries": [entry] * 11})


def test_audio_generation_refuses_existing_different_file(tmp_path, monkeypatch):
    from scripts import generate_showcase_audio as synth

    path = tmp_path / f"{synth.DEMO_TRACKS[0]['id']}.wav"
    path.write_bytes(b"existing audio must survive")
    monkeypatch.setattr(synth, "synthesize_demo", lambda _: b"new generated audio")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        generate_demos(tmp_path)
    assert path.read_bytes() == b"existing audio must survive"
