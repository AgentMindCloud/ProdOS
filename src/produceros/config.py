"""Application configuration.

ProducerOS runs with zero configuration. Every value here has a safe local
default. Values can be overridden by environment variables prefixed
``PRODUCEROS_`` or by a ``config.toml`` file in the data directory (see
``config.example.toml``). Environment variables take precedence.

The data directory is the single writable location ProducerOS uses for the
database, generated secret key, logs, and backups. It is never inside the
application/install directory, because that directory may be read-only
(e.g. when running from a PyInstaller-built, admin-installed location).
"""

from __future__ import annotations

import os
import secrets
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "ProducerOS"
DEFAULT_PORT = 8420
DEFAULT_MCP_PORT = 8421
SECRET_KEY_FILENAME = "secret.key"  # nosec B105 - a filename constant, not a credential
CONFIG_FILENAME = "config.toml"

ALLOWED_SCANNER_EXTENSIONS: tuple[str, ...] = (
    ".flp", ".zip", ".wav", ".aiff", ".aif", ".mp3", ".flac", ".ogg", ".m4a",
    ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".pdf", ".txt", ".csv",
)


def default_data_dir() -> Path:
    """Return the platform-appropriate writable data directory.

    Windows: %LOCALAPPDATA%\\ProducerOS
    macOS/Linux (dev/CI use): ~/.local/share/produceros
    """
    env_override = os.environ.get("PRODUCEROS_DATA_DIR")
    if env_override:
        return Path(env_override)

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "ProducerOS"

    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "produceros"


def _load_toml_overrides(data_dir: Path) -> dict:
    config_path = data_dir / CONFIG_FILENAME
    if not config_path.exists():
        return {}
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)
    flat: dict[str, object] = {}
    section_map = {
        "server": {"bind_mode": "bind_mode", "port": "port", "open_browser": "open_browser"},
        "database": {"wal_mode": "db_wal_mode"},
        "security": {
            "session_minutes": "session_minutes",
            "login_rate_limit_per_minute": "login_rate_limit_per_minute",
            "pairing_rate_limit_per_minute": "pairing_rate_limit_per_minute",
            "pairing_code_ttl_minutes": "pairing_code_ttl_minutes",
        },
        "audio": {"ffmpeg_path": "ffmpeg_path", "ffprobe_path": "ffprobe_path"},
        "scanner": {
            "roots": "scanner_roots",
            "allowed_extensions": "scanner_allowed_extensions",
            "max_file_size_mb": "scanner_max_file_size_mb",
        },
        "mcp": {"enabled": "mcp_enabled", "bind": "mcp_bind", "port": "mcp_port"},
        "logging": {"level": "log_level"},
    }
    for section, keys in section_map.items():
        section_values = raw.get(section, {})
        for toml_key, field_name in keys.items():
            if toml_key in section_values:
                flat[field_name] = section_values[toml_key]
    return flat


class Settings(BaseSettings):
    """Runtime settings. See config.example.toml / .env.example for docs."""

    model_config = SettingsConfigDict(env_prefix="PRODUCEROS_", extra="ignore")

    app_env: str = "production"
    data_dir: Path = Field(default_factory=default_data_dir)

    bind_mode: str = "desktop"  # "desktop" | "lan"
    port: int = DEFAULT_PORT
    open_browser: bool = True

    db_wal_mode: bool = True

    session_minutes: int = 720
    login_rate_limit_per_minute: int = 5
    pairing_rate_limit_per_minute: int = 5
    pairing_code_ttl_minutes: int = 10

    ffmpeg_path: str = ""
    ffprobe_path: str = ""

    scanner_roots: list[str] = Field(default_factory=list)
    scanner_allowed_extensions: list[str] = Field(
        default_factory=lambda: list(ALLOWED_SCANNER_EXTENSIONS)
    )
    scanner_max_file_size_mb: int = 4096

    mcp_enabled: bool = False
    mcp_bind: str = "127.0.0.1"
    mcp_port: int = DEFAULT_MCP_PORT

    log_level: str = "INFO"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "produceros.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def secret_key_path(self) -> Path:
        return self.data_dir / SECRET_KEY_FILENAME

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def audio_cache_dir(self) -> Path:
        return self.data_dir / "audio_cache"

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.logs_dir, self.backups_dir, self.audio_cache_dir):
            path.mkdir(parents=True, exist_ok=True)

    def load_or_create_secret_key(self) -> str:
        """Return the local session-signing secret, generating it on first run.

        The secret never lives in the repository or in version control; it is
        written once to the data directory with restrictive permissions.
        """
        self.ensure_directories()
        if self.secret_key_path.exists():
            return self.secret_key_path.read_text(encoding="utf-8").strip()
        key = secrets.token_urlsafe(48)
        self.secret_key_path.write_text(key, encoding="utf-8")
        try:
            os.chmod(self.secret_key_path, 0o600)
        except OSError:
            pass  # best-effort on platforms without POSIX permissions (Windows)
        return key


@lru_cache
def get_settings() -> Settings:
    """Return process-wide cached settings, merging config.toml overrides.

    Environment variables (handled natively by pydantic-settings) always win
    over config.toml, which always wins over built-in defaults.
    """
    data_dir = default_data_dir()
    toml_overrides = _load_toml_overrides(data_dir)
    env_keys = {k[len("PRODUCEROS_"):].lower() for k in os.environ if k.startswith("PRODUCEROS_")}
    for key in list(toml_overrides):
        if key in env_keys:
            toml_overrides.pop(key)
    return Settings(**toml_overrides)


def reset_settings_cache() -> None:
    """Clear the cached settings singleton (used by tests)."""
    get_settings.cache_clear()
