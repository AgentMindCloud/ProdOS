from produceros.logging_config import redact_secrets


def test_redacts_password_field():
    assert "hunter2" not in redact_secrets('login attempt: {"password": "hunter2"}')


def test_redacts_authorization_bearer_header():
    redacted = redact_secrets("Authorization: Bearer abc123.def456")
    assert "abc123.def456" not in redacted


def test_redacts_session_token():
    redacted = redact_secrets("session_token=sekrit-value-1234")
    assert "sekrit-value-1234" not in redacted


def test_redacts_pairing_code():
    redacted = redact_secrets("pairing_code: ABCD1234")
    assert "ABCD1234" not in redacted


def test_redacts_secret_key():
    redacted = redact_secrets("secret_key=abcdef0123456789")
    assert "abcdef0123456789" not in redacted


def test_redacts_csrf_token():
    redacted = redact_secrets("csrf_token=xyz-789")
    assert "xyz-789" not in redacted


def test_leaves_unrelated_text_untouched():
    message = "Project 'Midnight Run' scanned: 12 files found."
    assert redact_secrets(message) == message


def test_configured_logger_actually_redacts_on_write(tmp_path):
    from produceros.logging_config import configure_logging, get_logger

    configure_logging(tmp_path / "logs", level="INFO")
    logger = get_logger("test")
    logger.info('user submitted password="hunter2"')

    log_file = tmp_path / "logs" / "produceros.log"
    contents = log_file.read_text()
    assert "hunter2" not in contents
    assert "[REDACTED]" in contents
