from produceros.scanners.hashing import hash_file


def test_identical_content_same_hash(tmp_path):
    file_a = tmp_path / "a.wav"
    file_b = tmp_path / "b.wav"
    file_a.write_bytes(b"identical content" * 100)
    file_b.write_bytes(b"identical content" * 100)
    assert hash_file(file_a) == hash_file(file_b)


def test_different_content_different_hash(tmp_path):
    file_a = tmp_path / "a.wav"
    file_b = tmp_path / "b.wav"
    file_a.write_bytes(b"content one")
    file_b.write_bytes(b"content two")
    assert hash_file(file_a) != hash_file(file_b)


def test_hash_is_stable_sha256_hex(tmp_path):
    path = tmp_path / "a.wav"
    path.write_bytes(b"hello world")
    digest = hash_file(path)
    assert len(digest) == 64
    int(digest, 16)  # raises ValueError if not valid hex
