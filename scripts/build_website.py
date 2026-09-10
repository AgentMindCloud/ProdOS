"""Build the standalone public launch site, separately from the desktop app.

Usage: python scripts/build_website.py
Only allowlisted public assets and the verified Windows ZIP are copied. No app
database, configuration, account, source checkout, or music library is deployed.
"""

from __future__ import annotations

import argparse
import array
import hashlib
import html
import json
import math
import random
import re
import shutil
import sys
import wave
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

if __package__:
    from .generate_showcase_audio import DEMO_TRACKS, generate_demos
else:
    # The documented direct-script command uses the same module without a package.
    from generate_showcase_audio import DEMO_TRACKS, generate_demos  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
APP_VERSION = "0.2.1"
RELEASE_DATE = "2026-09-10"
APP_NAME = f"ProducerOS-{APP_VERSION}-Windows.zip"
DOMAIN = "https://prodos.tech"
# Reviewed packaged Windows smoke and ZIP integrity passed on 2026-09-10.
EXPECTED_APP_SHA256: str | None = "b2a4eba0421139bd6c4c70b9a8ace2494e4f7e80e89bcda43a28cca8cb224863"


def mailto(subject: str, body: str) -> str:
    return (
        "mailto:contact@prodos.tech?subject="
        + quote(subject, safe="")
        + "&body="
        + quote(body, safe="")
    )


def clip_platform(url: str) -> str:
    """Accept direct public music-page links only; never fetch remote content."""
    if not isinstance(url, str) or len(url) > 400 or any(c.isspace() for c in url):
        raise ValueError("Clip URL must be a short public HTTPS music-page link.")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.password or parts.port or parts.fragment:
        raise ValueError("Clip URL must use HTTPS with no credentials, port or fragment.")
    host = parts.netloc.lower()
    if (
        host in {"soundcloud.com", "www.soundcloud.com"}
        and not parts.query
        and re.fullmatch(r"/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/?", parts.path)
    ):
        return "SoundCloud"
    if (
        re.fullmatch(r"[a-z0-9-]+\.bandcamp\.com", host)
        and not parts.query
        and re.fullmatch(r"/track/[a-zA-Z0-9_-]+/?", parts.path)
    ):
        return "Bandcamp"
    if (
        host == "open.spotify.com"
        and not parts.query
        and re.fullmatch(r"/track/[a-zA-Z0-9]{22}", parts.path)
    ):
        return "Spotify"
    if host == "youtu.be" and not parts.query and re.fullmatch(r"/[a-zA-Z0-9_-]{11}", parts.path):
        return "YouTube"
    if host in {"youtube.com", "www.youtube.com"} and parts.path == "/watch":
        query = parse_qs(parts.query, keep_blank_values=True)
        if (
            set(query) == {"v"}
            and len(query["v"]) == 1
            and re.fullmatch(r"[a-zA-Z0-9_-]{11}", query["v"][0])
        ):
            return "YouTube"
    raise ValueError(
        "Use a direct SoundCloud, Bandcamp track, Spotify track or YouTube video URL without tracking parameters."
    )


def render_showcase(template: str, catalog: dict) -> str:
    if not isinstance(catalog, dict) or set(catalog) != {"entries"}:
        raise ValueError("Showcase catalog must contain only entries.")
    entries = catalog["entries"]
    if not isinstance(entries, list) or len(entries) > 10:
        raise ValueError("The first showcase accepts at most 10 reviewed producer entries.")
    cards, ids, producers = [], set(), set()
    required = {
        "id",
        "producer",
        "title",
        "url",
        "feedback_question",
        "duration_seconds",
        "publication_approved",
        "producer_permission_confirmed",
    }
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not required <= set(entry)
            or set(entry) - required - {"genre", "bpm"}
        ):
            raise ValueError(
                "Showcase entry has missing or unknown fields. Do not put private intake data here."
            )
        if (
            entry["publication_approved"] is not True
            or entry["producer_permission_confirmed"] is not True
        ):
            raise ValueError(
                "Every entry needs explicit producer permission and publication review."
            )
        for field, limit in (
            ("id", 60),
            ("producer", 60),
            ("title", 90),
            ("feedback_question", 240),
            ("genre", 40),
        ):
            value = entry.get(field, "")
            if (
                not isinstance(value, str)
                or (field != "genre" and not value.strip())
                or len(value) > limit
                or any(ord(c) < 32 for c in value)
            ):
                raise ValueError(f"Invalid showcase field: {field}")
        identifier = entry["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier) or identifier in ids:
            raise ValueError("Showcase IDs must be unique lowercase slugs.")
        producer = entry["producer"].strip().casefold()
        if producer in producers:
            raise ValueError("The first group allows one clip per producer.")
        ids.add(identifier)
        producers.add(producer)
        duration = entry["duration_seconds"]
        if type(duration) is not int or not 30 <= duration <= 60:
            raise ValueError("Review a 30–60 second clip before listing it.")
        bpm = entry.get("bpm")
        if bpm is not None and (type(bpm) is not int or not 1 <= bpm <= 400):
            raise ValueError("BPM must be a supplied number or omitted.")
        platform = clip_platform(entry["url"])
        title, name, question = (
            html.escape(entry[field]) for field in ("title", "producer", "feedback_question")
        )
        meta = f"<span>{duration} sec</span>"
        if entry.get("genre"):
            meta += f"<span>{html.escape(entry['genre'])}</span>"
        if bpm is not None:
            meta += f"<span>{bpm} BPM</span>"
        feedback = mailto(
            f"Showcase feedback: {entry['title']}",
            f"Listing: {DOMAIN}/showcase.html#clip-{identifier}\n\nMy feedback:\n\nMay this feedback be shared with the producer? [yes/no]\n",
        )
        cards.append(
            f'<article class="clip-card" id="clip-{identifier}"><p class="eyebrow">PRODUCER SUBMISSION · {platform.upper()}</p><h3>{title}</h3><p class="clip-producer">By {name}</p><div class="clip-meta">{meta}</div><div class="clip-question"><p class="micro-label">THE PRODUCER ASKS</p><p>{question}</p></div><div class="clip-actions"><a class="button button-primary" href="{html.escape(entry["url"], quote=True)}" target="_blank" rel="noopener noreferrer">Listen on {platform} <span aria-hidden="true">↗</span><span class="sr-only">: {title}</span></a><a class="text-link" href="{html.escape(feedback, quote=True)}">Email feedback<span class="sr-only">: {title}</span></a></div></article>'
        )
    content = (
        '<div class="showcase-grid">' + "".join(cards) + "</div>"
        if cards
        else '<div class="showcase-empty"><div><h3>The first producers start here.</h3><p>No producer clips are published yet. Put a link forward for review and help shape the first listening group.</p></div><a class="button button-outline" href="#take-part">Be part of the first group <span aria-hidden="true">↗</span></a></div>'
    )
    demos = []
    for track in DEMO_TRACKS:
        title = html.escape(track["title"])
        demos.append(
            f'<article class="clip-card demo-beat" id="demo-{track["id"]}"><div class="demo-beat-cover" aria-hidden="true"><span>{html.escape(track["artist"])}</span><strong>{title}</strong></div><p class="eyebrow">GENERATED DEMO · FICTIONAL ARTIST</p><h3>{title}</h3><p class="clip-producer">{html.escape(track["artist"])}</p><div class="clip-meta"><span>{track["genre"]}</span><span>{track["bpm"]} BPM</span><span>{track["key"]}</span></div><audio controls preload="none" aria-label="Play {title} by {html.escape(track["artist"])}"><source src="assets/showcase/{track["id"]}.wav" type="audio/wav">Your browser cannot play this audio. <a href="assets/showcase/{track["id"]}.wav">Open {title} audio</a>.</audio><div class="clip-question"><p class="micro-label">A QUESTION TO TRY</p><p>{html.escape(track["question"])}</p></div></article>'
        )
    submission = mailto(
        "Producer showcase submission",
        "Producer name:\nTrack title:\nPublic 30–60 second clip URL (no attachments):\nGenre / BPM (optional):\nOne feedback question:\n\nPublication permission (required): [Please explicitly state whether ProducerOS may feature your link, producer name, track title and question publicly.]\n\nRights confirmation (required): [Please confirm you have the necessary rights and collaborator permissions to share this clip.]\n",
    )
    replacements = {
        "SHOWCASE_CONTENT": content,
        "DEMO_CONTENT": '<div class="showcase-grid demo-beats">' + "".join(demos) + "</div>",
        "PUBLISHED_COUNT": f"{len(entries)} producer clip{'s' if len(entries) != 1 else ''} published",
        "SUBMISSION_URL": html.escape(submission, quote=True),
        "REPORT_URL": html.escape(
            mailto(
                "Showcase correction or concern",
                "Listing URL:\nRequested correction, unlisting or concern:\nDetails:\n",
            ),
            quote=True,
        ),
    }
    for token in replacements:
        if "{{" + token + "}}" not in template:
            raise ValueError(f"Missing showcase template token: {token}")
    return re.sub(
        r"\{\{(" + "|".join(replacements) + r")\}\}", lambda match: replacements[match[1]], template
    )


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def validate_app_archive(path: Path) -> None:
    if EXPECTED_APP_SHA256 is None:
        raise ValueError(
            f"The reviewed {APP_VERSION} Windows ZIP hash is pending. "
            "Verify the new package and pin its SHA-256 before building the public website."
        )
    if not path.is_file():
        raise ValueError(
            f"Missing reviewed Windows package: {path}. Build with scripts/build_windows.ps1, "
            "package the complete dist/ProducerOS folder, then review and update the release hash."
        )
    if sha256(path) != EXPECTED_APP_SHA256:
        raise ValueError(
            f"Windows ZIP differs from the reviewed {APP_VERSION} package; review before publishing."
        )
    with zipfile.ZipFile(path) as package:
        if "ProducerOS/ProducerOS.exe" not in package.namelist():
            raise ValueError("The package does not contain the expected executable.")
        if package.testzip():
            raise ValueError("Windows package ZIP integrity check failed.")
        for name in package.namelist():
            item = Path(name)
            if ".." in item.parts or item.is_absolute():
                raise ValueError("Unexpected path in Windows package.")
            if item.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".key", ".log"}:
                raise ValueError("Private/runtime data must not be distributed.")
            if item.name.lower() in {"config.toml", ".env", "secret.key"}:
                raise ValueError("Configuration or secrets must not be distributed.")


def generate_demo_loop(path: Path) -> None:
    """An original synthesized 8-bar loop, generated locally with no samples.

    A browser demo asset only. This never reads or modifies a producer's audio.
    """
    rate = 22050
    beat = 60 / 112
    seconds = beat * 32
    total = round(rate * seconds)
    rng = random.Random(20260909)
    samples = [0.0] * total

    def voice(start: float, duration: float, note: float, gain: float, kind: str) -> None:
        offset = round(start * rate)
        count = min(round(duration * rate), total - offset)
        for index in range(count):
            t = index / rate
            if kind == "kick":
                phase = 2 * math.pi * (48 * t + 85 * 0.022 * (1 - math.exp(-t / 0.022)))
                value = math.sin(phase) * math.exp(-t * 13)
            elif kind == "hat":
                value = rng.uniform(-1, 1) * math.exp(-t * 80)
            elif kind == "pad":
                envelope = min(t / 0.08, 1) * min((duration - t) / 0.3, 1)
                value = (
                    math.sin(2 * math.pi * note * t) + 0.2 * math.sin(4 * math.pi * note * t)
                ) * envelope
            else:
                value = math.sin(2 * math.pi * note * t) * math.exp(-t * 8) * min(t / 0.006, 1)
            samples[offset + index] += gain * value

    for step in range(32):
        voice(step * beat, 0.45, 0, 0.40, "kick")
        voice((step + 0.5) * beat, 0.08, 0, 0.045, "hat")
        if step % 2:
            voice(step * beat, 0.1, 0, 0.055, "hat")
    chords = [
        (220, 261.6256, 329.6276),
        (174.6141, 220, 261.6256),
        (130.8128, 164.8138, 195.9977),
        (195.9977, 246.9417, 293.6648),
    ]
    for bar in range(8):
        chord = chords[(bar // 2) % len(chords)]
        for note in chord:
            voice(bar * beat * 4, beat * 3.85, note / 2, 0.055, "pad")
        for step in range(8):
            voice((bar * 4 + step / 2) * beat, beat * 0.75, chord[step % 3] * 2, 0.085, "bell")
    pcm = array.array("h")
    for index, sample in enumerate(samples):
        fade = min(index / (rate * 0.025), (total - 1 - index) / (rate * 0.06), 1)
        pcm.append(round(max(-1, min(1, sample * fade)) * 28000))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())


def build(output: Path, archive: Path, app_zip: Path) -> dict:
    output = output.resolve()
    archive = archive.resolve()
    # All generated targets must remain in this repository's explicit build areas.
    allowed = (ROOT / ".work").resolve()
    release = (ROOT / "release-artifacts").resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("Website output must be a subdirectory of this repository's .work/.")
    if not archive.is_relative_to(release):
        raise ValueError("Deployment archive must be in this repository's release-artifacts/.")
    validate_app_archive(app_zip)
    source = ROOT / "website"
    for filename in (
        "index.html",
        "site.css",
        "site.js",
        "showcase.html",
        "showcase.css",
        "showcase.js",
        "showcase.json",
    ):
        if not (source / filename).is_file():
            raise ValueError(f"Missing website source: {filename}")
    output.mkdir(parents=True, exist_ok=True)
    public_files: list[Path] = []

    def copy(src: Path, relative: str) -> None:
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, destination)
        public_files.append(destination)

    def write(relative: str, content: str) -> None:
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        public_files.append(destination)

    index = (source / "index.html").read_text(encoding="utf-8")
    size_token = "{{APP_DOWNLOAD_SIZE}}"
    if index.count(size_token) != 1:
        raise ValueError("The website source must contain exactly one download-size placeholder.")
    write("index.html", index.replace(size_token, f"{app_zip.stat().st_size / 1_000_000:.1f} MB"))
    write(
        "showcase.html",
        render_showcase(
            (source / "showcase.html").read_text(encoding="utf-8"),
            json.loads((source / "showcase.json").read_text(encoding="utf-8")),
        ),
    )
    for filename in ("site.css", "site.js", "showcase.css", "showcase.js"):
        copy(source / filename, filename)
    copy(ROOT / "src/produceros/web/static/artwork/studio-disc.png", "assets/studio-disc.png")
    copy(ROOT / "src/produceros/web/static/icons/icon-192.png", "assets/app-icon.png")
    copy(ROOT / "docs/review-2026-09-09/02-dashboard-after.png", "assets/dashboard.png")
    copy(ROOT / "docs/review-2026-09-09/02-dashboard-after.png", "assets/share-card.png")
    demo = output / "assets/demo-loop.wav"
    generate_demo_loop(demo)
    public_files.append(demo)
    public_files.extend(generate_demos(output / "assets/showcase"))
    copy(app_zip, f"downloads/{APP_NAME}")
    write(f"downloads/{APP_NAME}.sha256", f"{EXPECTED_APP_SHA256}  {APP_NAME}\n")
    write("downloads/SHA256SUMS.txt", f"{EXPECTED_APP_SHA256}  {APP_NAME}\n")
    copy(ROOT / "docs/review-2026-09-10/WINDOWS_PORTABLE.txt", "downloads/READ-ME-FIRST.txt")
    copy(ROOT / "LICENSE", "downloads/LICENSE.txt")
    release_info = {
        "product": "ProducerOS",
        "version": APP_VERSION,
        "channel": "preview",
        "platform": "Windows",
        "format": "portable-zip",
        "date": RELEASE_DATE,
        "url": f"downloads/{APP_NAME}",
        "bytes": app_zip.stat().st_size,
        "sha256": EXPECTED_APP_SHA256,
        "automatic_update": False,
    }
    write("release.json", json.dumps(release_info, indent=2) + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    write(
        "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{DOMAIN}/</loc></url>'
        f"<url><loc>{DOMAIN}/showcase.html</loc></url></urlset>\n",
    )
    write(
        ".htaccess",
        """Options -Indexes
DirectoryIndex index.html
AddType application/zip .zip
<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set X-Frame-Options "DENY"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  Header always set Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'"
  <FilesMatch "\\.(html|json)$">
    Header set Cache-Control "no-cache"
  </FilesMatch>
  <FilesMatch "\\.(css|js|png|wav)$">
    Header set Cache-Control "public, max-age=3600"
  </FilesMatch>
  <FilesMatch "\\.zip$">
    Header set Cache-Control "public, max-age=86400"
    Header set Content-Disposition "attachment"
  </FilesMatch>
</IfModule>
""",
    )
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as deploy:
        for file in sorted(public_files):
            deploy.write(file, file.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as deploy:
        if deploy.testzip():
            raise ValueError("Deployment ZIP integrity check failed.")
    manifest = {
        "domain": DOMAIN,
        "archive": archive.name,
        "sha256": sha256(archive),
        "bytes": archive.stat().st_size,
        "file_count": len(public_files),
        "files": {p.relative_to(output).as_posix(): sha256(p) for p in sorted(public_files)},
    }
    archive.with_suffix(".zip.sha256").write_text(
        f"{manifest['sha256']}  {archive.name}\n", encoding="ascii"
    )
    archive.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".work/website-dist")
    parser.add_argument(
        "--archive", type=Path, default=ROOT / "release-artifacts/prodos-site-20260910.zip"
    )
    parser.add_argument("--app-zip", type=Path, default=ROOT / "release-artifacts" / APP_NAME)
    args = parser.parse_args()
    result = build(args.output, args.archive, args.app_zip)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
