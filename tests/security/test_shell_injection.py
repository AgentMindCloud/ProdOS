"""FFmpeg/FFprobe are only ever invoked with a fixed argument list, never
via a shell, so shell metacharacters in a filename cannot be interpreted."""

from __future__ import annotations

import ast
import inspect

from produceros.audio import ffmpeg as ffmpeg_module


def test_ffmpeg_subprocess_calls_never_use_shell_true():
    """Walk the actual AST (not a text search, which would also flag the
    module's own docstring warning against shell=True) and confirm every
    subprocess.run call passes a list as its first argument and never
    sets shell=True."""
    tree = ast.parse(inspect.getsource(ffmpeg_module))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
    ]
    assert calls, "expected at least one subprocess.run call to check"
    for call in calls:
        assert call.args and isinstance(call.args[0], ast.List)
        for keyword in call.keywords:
            if keyword.arg == "shell":
                assert not (isinstance(keyword.value, ast.Constant) and keyword.value.value is True)


def test_probe_codec_info_treats_shell_metacharacters_as_a_literal_filename(tmp_path, monkeypatch):
    """A filename containing shell metacharacters must be passed through
    argv untouched, not interpreted -- confirmed by pointing ffprobe at a
    nonexistent path built from that name and checking it just fails
    cleanly (no injected side effects, no exception escapes)."""
    dangerous_name = tmp_path / "track$(touch pwned).wav"

    result = ffmpeg_module.probe_codec_info(dangerous_name)

    assert result is None
    assert not (tmp_path / "pwned").exists()


def test_analyze_loudness_treats_shell_metacharacters_as_a_literal_filename(tmp_path):
    dangerous_name = tmp_path / "track; rm -rf ~ #.wav"

    result = ffmpeg_module.analyze_loudness(dangerous_name)

    assert result is not None
    assert not (tmp_path / "pwned").exists()
