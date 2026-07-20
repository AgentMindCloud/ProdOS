"""Filename and version parsing (spec section 10).

Recognizes common producer filename conventions and extracts structured
data *without ever renaming the original file*. Patterns are tried in
order; the list is intentionally a plain Python sequence rather than a
config file for the MVP, but each pattern is isolated so new conventions
can be added without touching the others (see docs/DATA_MODEL.md).

Examples this module is built to handle:
    Artist_TrackName_MIX_v03_2026-07-19.wav
    Artist - Track Name - Master v2.wav
    TrackName_Instrumental_120BPM_Am.wav
    TrackName_FL_v12.flp
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

STAGE_KEYWORDS: dict[str, str] = {
    "MIX": "mix",
    "MASTER": "master",
    "INSTRUMENTAL": "instrumental",
    "ACAPELLA": "acapella",
    "CLEAN": "clean",
    "STEMS": "stems",
    "MASTERED": "master",
}

# NOTE: these use lookaround boundaries, not \b -- producer filenames are
# underscore-delimited, and underscore counts as a "word" character to \b,
# so `\b` silently fails to match at an "_2026" or "_v03" boundary.
_DATE_RE = re.compile(r"(?<![0-9])(\d{4}-\d{2}-\d{2})(?![0-9])")
_VERSION_RE = re.compile(r"(?<![A-Za-z0-9])v(\d{1,3})(?![A-Za-z0-9])", re.IGNORECASE)
_BPM_RE = re.compile(r"(?<![A-Za-z0-9])(\d{2,3})\s*BPM(?![A-Za-z0-9])", re.IGNORECASE)
_KEY_AFTER_BPM_RE = re.compile(
    r"\d{2,3}\s*BPM[_\s]+([A-Ga-g][#b]?m?)(?![A-Za-z0-9])", re.IGNORECASE
)
_FL_VERSION_RE = re.compile(r"^(?P<track>.+?)_FL_v(?P<version>\d+)$", re.IGNORECASE)


@dataclass
class ParsedFilename:
    original_filename: str
    artist: str | None = None
    track: str | None = None
    mix_or_master: str | None = None
    version_number: int | None = None
    version_label: str | None = None
    parsed_date: date | None = None
    bpm: float | None = None
    musical_key: str | None = None
    asset_hint: str | None = None
    raw_tokens: list[str] = field(default_factory=list)

    def as_metadata_dict(self) -> dict:
        return {
            "artist": self.artist,
            "track": self.track,
            "mix_or_master": self.mix_or_master,
            "version_number": self.version_number,
            "version_label": self.version_label,
            "date": self.parsed_date.isoformat() if self.parsed_date else None,
            "bpm": self.bpm,
            "musical_key": self.musical_key,
            "asset_hint": self.asset_hint,
        }


def _title_case_token(token: str) -> str:
    return token.replace("-", " ").replace(".", " ").strip()


def parse_filename(filename: str) -> ParsedFilename:
    stem = Path(filename).stem
    result = ParsedFilename(original_filename=filename)

    fl_match = _FL_VERSION_RE.match(stem)
    if fl_match:
        result.track = _title_case_token(fl_match.group("track"))
        result.version_number = int(fl_match.group("version"))
        result.version_label = f"v{fl_match.group('version')}"
        result.asset_hint = "fl_project"
        return result

    date_match = _DATE_RE.search(stem)
    if date_match:
        with contextlib.suppress(ValueError):
            result.parsed_date = date.fromisoformat(date_match.group(1))

    version_match = _VERSION_RE.search(stem)
    if version_match:
        result.version_number = int(version_match.group(1))
        result.version_label = f"v{version_match.group(1)}"

    bpm_match = _BPM_RE.search(stem)
    if bpm_match:
        result.bpm = float(bpm_match.group(1))
        key_match = _KEY_AFTER_BPM_RE.search(stem)
        if key_match:
            result.musical_key = key_match.group(1)

    for keyword, normalized in STAGE_KEYWORDS.items():
        if re.search(rf"(?<![A-Za-z0-9]){keyword}(?![A-Za-z0-9])", stem, re.IGNORECASE):
            result.mix_or_master = normalized
            break

    if " - " in stem:
        parts = [p.strip() for p in stem.split(" - ") if p.strip()]
        result.raw_tokens = parts
        if len(parts) >= 1:
            result.artist = parts[0]
        if len(parts) >= 2:
            result.track = parts[1]
        return result

    tokens = [t for t in stem.split("_") if t]
    result.raw_tokens = tokens

    def is_consumed(token: str) -> bool:
        if date_match and token == date_match.group(1):
            return True
        if re.fullmatch(r"[vV]\d{1,3}", token):
            return True
        if re.fullmatch(r"\d{2,3}BPM", token, re.IGNORECASE):
            return True
        if bpm_match and result.musical_key and token.lower() == result.musical_key.lower():
            return True
        return token.upper() in STAGE_KEYWORDS

    remaining = [t for t in tokens if not is_consumed(t)]
    if len(remaining) >= 2:
        result.artist = _title_case_token(remaining[0])
        result.track = _title_case_token(remaining[1])
    elif len(remaining) == 1:
        result.track = _title_case_token(remaining[0])

    return result
