"""Optional FFmpeg/FFprobe integration.

FFmpeg is auto-detected on PATH (or at a configured path) and used only to
*add* loudness/true-peak numbers on top of the Mutagen/wave baseline
(spec section 11). It is never required. All subprocess calls use an
argument list (never ``shell=True`` or string-built commands), per the
security requirements in spec section 19.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - used only with fixed argv lists below, never shell=True
from dataclasses import dataclass
from pathlib import Path

from produceros.config import get_settings

FFMPEG_TIMEOUT_SECONDS = 120


@dataclass
class FfmpegStatus:
    available: bool
    ffmpeg_path: str | None
    ffprobe_path: str | None


@dataclass
class LoudnessAnalysis:
    integrated_loudness_lufs: float | None = None
    loudness_range_lu: float | None = None
    true_peak_dbfs: float | None = None
    peak_level_dbfs: float | None = None
    codec_info: str | None = None
    warnings: list[str] | None = None


def _resolve_binary(configured_path: str, binary_name: str) -> str | None:
    if configured_path:
        candidate = Path(configured_path)
        return str(candidate) if candidate.exists() else None
    found = shutil.which(binary_name)
    return found


def ffmpeg_status() -> FfmpegStatus:
    settings = get_settings()
    ffmpeg_path = _resolve_binary(settings.ffmpeg_path, "ffmpeg")
    ffprobe_path = _resolve_binary(settings.ffprobe_path, "ffprobe")
    return FfmpegStatus(
        available=bool(ffmpeg_path and ffprobe_path),
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )


def probe_codec_info(path: str | Path) -> str | None:
    status = ffmpeg_status()
    if not status.available or status.ffprobe_path is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 # nosec B603 - fixed argv, no shell, path validated by caller
            [
                status.ffprobe_path,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-select_streams",
                "a:0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
        data = json.loads(result.stdout or "{}")
        streams = data.get("streams") or []
        if not streams:
            return None
        stream = streams[0]
        codec = stream.get("codec_name", "unknown")
        bitrate = stream.get("bit_rate")
        return f"{codec}" + (f" @ {int(bitrate) // 1000}kbps" if bitrate else "")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def analyze_loudness(path: str | Path) -> LoudnessAnalysis:
    """Run ffmpeg's loudnorm filter in analysis (dry-run) mode to obtain
    integrated loudness, loudness range, and true peak. Returns an empty
    result (with a warning) if FFmpeg is unavailable or analysis fails --
    ProducerOS must remain fully usable without it.
    """
    status = ffmpeg_status()
    if not status.available or status.ffmpeg_path is None:
        return LoudnessAnalysis(
            warnings=["FFmpeg not detected; advanced loudness analysis unavailable."]
        )

    try:
        result = subprocess.run(  # noqa: S603 # nosec B603 - fixed argv, no shell
            [
                status.ffmpeg_path,
                "-nostdin",
                "-hide_banner",
                "-i",
                str(path),
                "-af",
                "loudnorm=print_format=json",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
        stderr = result.stderr or ""
        start = stderr.rfind("{")
        end = stderr.rfind("}")
        if start == -1 or end == -1:
            return LoudnessAnalysis(warnings=["FFmpeg ran but did not return loudness JSON."])
        payload = json.loads(stderr[start : end + 1])
        codec_info = probe_codec_info(path)
        return LoudnessAnalysis(
            integrated_loudness_lufs=float(payload.get("input_i", "nan"))
            if payload.get("input_i")
            else None,
            loudness_range_lu=float(payload.get("input_lra", "nan"))
            if payload.get("input_lra")
            else None,
            true_peak_dbfs=float(payload.get("input_tp", "nan"))
            if payload.get("input_tp")
            else None,
            peak_level_dbfs=float(payload.get("input_tp", "nan"))
            if payload.get("input_tp")
            else None,
            codec_info=codec_info,
        )
    except (subprocess.SubprocessError, json.JSONDecodeError, ValueError, OSError) as exc:
        return LoudnessAnalysis(warnings=[f"FFmpeg loudness analysis failed: {exc}"])
