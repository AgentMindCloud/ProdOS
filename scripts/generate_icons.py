#!/usr/bin/env python3
"""Generate ProducerOS's local PWA/app icons as plain PNG files.

No external image libraries, no CDN, no copyrighted artwork: this writes
raw PNG bytes (IHDR/IDAT/IEND chunks, zlib-compressed via the standard
library) for a simple geometric "waveform bars" mark on a dark charcoal
background, in ProducerOS's brand colors. Re-run this script any time the
icon design changes; the outputs are committed to the repo like any other
static web asset (see docs/ANDROID_PWA.md).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

BACKGROUND = (26, 24, 22, 255)  # deep charcoal
ACCENT = (242, 140, 56, 255)  # warm orange
ACCENT_DIM = (196, 108, 40, 255)

ICONS_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "produceros" / "web" / "static" / "icons"
)
PACKAGING_DIR = Path(__file__).resolve().parent.parent / "packaging" / "pyinstaller"


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _png_bytes(pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    height = len(pixels)
    width = len(pixels[0])
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type: none
        for r, g, b, a in row:
            raw.extend((r, g, b, a))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _write_png(path: Path, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    path.write_bytes(_png_bytes(pixels))


def _write_ico(path: Path, sized_pixels: list[list[list[tuple[int, int, int, int]]]]) -> None:
    """Pack several square icon images into one multi-resolution .ico file.

    Windows has accepted PNG-compressed frames inside .ico containers since
    Vista, so each frame here is just the same PNG encoder used for the web
    icons -- no separate uncompressed-BMP encoder needed, no image library.
    """
    frames = [_png_bytes(pixels) for pixels in sized_pixels]
    count = len(frames)
    header = struct.pack("<HHH", 0, 1, count)  # reserved, type=icon, count

    entries = bytearray()
    offset = 6 + 16 * count  # ICONDIR + ICONDIRENTRY headers
    for pixels, frame in zip(sized_pixels, frames, strict=True):
        size = len(pixels)
        dim_byte = size if size < 256 else 0  # 0 means "256" per the ICO spec
        entries += struct.pack("<BBBBHHII", dim_byte, dim_byte, 0, 0, 1, 32, len(frame), offset)
        offset += len(frame)

    path.write_bytes(header + bytes(entries) + b"".join(frames))


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _blend(
    base: tuple[int, int, int, int], top: tuple[int, int, int, int], alpha: float
) -> tuple[int, int, int, int]:
    return (
        _lerp(base[0], top[0], alpha),
        _lerp(base[1], top[1], alpha),
        _lerp(base[2], top[2], alpha),
        255,
    )


def _rounded_mask(x: int, y: int, size: int, radius: int) -> bool:
    """True if (x, y) is inside a square-with-rounded-corners of the given size."""
    corners = [
        (radius, radius),
        (size - radius - 1, radius),
        (radius, size - radius - 1),
        (size - radius - 1, size - radius - 1),
    ]
    if x < radius and y < radius:
        return (x - corners[0][0]) ** 2 + (y - corners[0][1]) ** 2 <= radius**2
    if x > size - radius - 1 and y < radius:
        return (x - corners[1][0]) ** 2 + (y - corners[1][1]) ** 2 <= radius**2
    if x < radius and y > size - radius - 1:
        return (x - corners[2][0]) ** 2 + (y - corners[2][1]) ** 2 <= radius**2
    if x > size - radius - 1 and y > size - radius - 1:
        return (x - corners[3][0]) ** 2 + (y - corners[3][1]) ** 2 <= radius**2
    return True


def _generate(size: int, *, maskable: bool) -> list[list[tuple[int, int, int, int]]]:
    pixels = [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]
    radius = 0 if maskable else size // 6
    content_scale = 0.55 if maskable else 0.7  # maskable icons need extra safe-zone padding

    bar_count = 5
    bar_width = size * content_scale / (bar_count * 1.6)
    gap = bar_width * 0.6
    total_width = bar_count * bar_width + (bar_count - 1) * gap
    start_x = (size - total_width) / 2
    heights = [0.35, 0.6, 0.95, 0.6, 0.35]
    max_bar_height = size * content_scale

    for y in range(size):
        for x in range(size):
            if radius and not _rounded_mask(x, y, size, radius):
                continue
            pixels[y][x] = BACKGROUND

    for i, h_ratio in enumerate(heights):
        bar_height = max_bar_height * h_ratio
        x0 = start_x + i * (bar_width + gap)
        x1 = x0 + bar_width
        y1 = size / 2 + max_bar_height / 2
        y0 = y1 - bar_height
        color = ACCENT if i % 2 == 0 else ACCENT_DIM
        for y in range(int(y0), int(y1)):
            if y < 0 or y >= size:
                continue
            for x in range(int(x0), int(x1)):
                if x < 0 or x >= size:
                    continue
                if radius and not _rounded_mask(x, y, size, radius):
                    continue
                pixels[y][x] = color

    return pixels


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-192.png", 192, True),
        ("icon-maskable-512.png", 512, True),
        ("favicon-32.png", 32, False),
        ("apple-touch-icon-180.png", 180, False),
    ]
    for filename, size, maskable in targets:
        pixels = _generate(size, maskable=maskable)
        _write_png(ICONS_DIR / filename, pixels)
        print(f"wrote {filename} ({size}x{size}, maskable={maskable})")

    # Windows .ico for the frozen exe (PyInstaller's EXE(icon=...)) and the
    # Inno Setup installer (SetupIconFile) -- same non-maskable mark at the
    # standard Windows icon sizes, packed into one multi-resolution file.
    PACKAGING_DIR.mkdir(parents=True, exist_ok=True)
    ico_sizes = [16, 32, 48, 256]
    ico_path = PACKAGING_DIR / "app-icon.ico"
    _write_ico(ico_path, [_generate(size, maskable=False) for size in ico_sizes])
    print(
        f"wrote {ico_path.relative_to(PACKAGING_DIR.parent.parent)} ({', '.join(str(s) for s in ico_sizes)})"
    )


if __name__ == "__main__":
    main()
