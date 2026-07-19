import pytest

from produceros.security import (
    PathSecurityError,
    generate_pairing_code,
    hash_password,
    is_allowed_extension,
    is_within_size_limit,
    resolve_within_allowed_roots,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correcthorsebattery")
    assert verify_password(hashed, "correcthorsebattery")
    assert not verify_password(hashed, "wrong-password")


def test_password_hash_is_not_plaintext():
    hashed = hash_password("correcthorsebattery")
    assert "correcthorsebattery" not in hashed


def test_pairing_code_format():
    code = generate_pairing_code()
    assert len(code) == 8
    assert "0" not in code and "O" not in code and "1" not in code and "I" not in code


def test_pairing_codes_are_unique():
    codes = {generate_pairing_code() for _ in range(50)}
    assert len(codes) > 45  # astronomically unlikely to collide meaningfully


def test_resolve_within_allowed_roots_accepts_valid_path(tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    file_path = root / "track.wav"
    file_path.write_text("x")
    resolved = resolve_within_allowed_roots(file_path, [str(root)])
    assert resolved == file_path.resolve()


def test_resolve_within_allowed_roots_rejects_path_traversal(tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("x")
    traversal_path = root / ".." / "secret.txt"
    with pytest.raises(PathSecurityError):
        resolve_within_allowed_roots(traversal_path, [str(root)])


def test_resolve_within_allowed_roots_rejects_unrelated_path(tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    other = tmp_path / "Other"
    other.mkdir()
    with pytest.raises(PathSecurityError):
        resolve_within_allowed_roots(other / "file.wav", [str(root)])


def test_resolve_within_allowed_roots_rejects_symlink_escape(tmp_path):
    root = tmp_path / "Music"
    root.mkdir()
    outside_target = tmp_path / "outside.wav"
    outside_target.write_text("x")
    symlink = root / "escape.wav"
    try:
        symlink.symlink_to(outside_target)
    except OSError:
        pytest.skip("Symlinks not supported in this environment.")
    with pytest.raises(PathSecurityError):
        resolve_within_allowed_roots(symlink, [str(root)])


def test_is_allowed_extension():
    assert is_allowed_extension("track.wav", [".wav", ".mp3"])
    assert not is_allowed_extension("track.exe", [".wav", ".mp3"])


def test_is_within_size_limit():
    assert is_within_size_limit(10 * 1024 * 1024, max_mb=100)
    assert not is_within_size_limit(200 * 1024 * 1024, max_mb=100)
