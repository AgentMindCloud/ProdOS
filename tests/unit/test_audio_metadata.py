from produceros.audio.metadata import extract_metadata
from produceros.demo.audio_fixtures import generate_sine_wav


def test_wav_stdlib_extraction(tmp_path):
    path = generate_sine_wav(tmp_path / "tone.wav", seconds=1.0, sample_rate=44100, bit_depth=16, channels=1)
    meta = extract_metadata(path)
    assert meta.is_audio
    assert meta.sample_rate == 44100
    assert meta.bit_depth == 16
    assert meta.channels == 1
    assert meta.duration_seconds == 1.0


def test_non_audio_file_does_not_raise(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    meta = extract_metadata(path)
    assert meta.is_audio is False
    assert meta.file_type == "txt"


def test_missing_file_returns_warning_not_exception(tmp_path):
    meta = extract_metadata(tmp_path / "does_not_exist.wav")
    assert meta.warnings
