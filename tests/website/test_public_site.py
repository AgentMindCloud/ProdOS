"""Check the built public site, its download, and its browser interactions.

Run scripts/build_website.py first. These tests never start or expose the
desktop application's backend or use its real data directory.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BUILT = ROOT / ".work/website-dist"


@pytest.fixture(scope="module")
def site_url():
    assert (BUILT / "index.html").is_file(), "Build the website before running its browser tests."
    spec = importlib.util.spec_from_file_location(
        "preview_website", ROOT / "scripts/preview_website.py"
    )
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(preview.create_app(), log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=3)
        listener.close()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        yield browser
        browser.close()


def test_public_download_matches_reviewed_windows_package(site_url):
    release = httpx.get(f"{site_url}/release.json").json()
    assert release["version"] == "0.2.1"
    assert release["date"] == "2026-09-10"
    assert release["url"] == "downloads/ProducerOS-0.2.1-Windows.zip"
    digest = hashlib.sha256()
    size = 0
    with httpx.stream("GET", f"{site_url}/{release['url']}", timeout=30) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/zip")
        for chunk in response.iter_bytes():
            size += len(chunk)
            digest.update(chunk)
    reviewed_package = ROOT / "release-artifacts/ProducerOS-0.2.1-Windows.zip"
    with reviewed_package.open("rb") as source:
        reviewed_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    assert digest.hexdigest() == reviewed_sha256 == release["sha256"]
    assert size == reviewed_package.stat().st_size == release["bytes"]
    homepage = httpx.get(site_url).text
    assert f"Windows preview · ZIP · {size / 1_000_000:.1f} MB" in homepage
    assert "{{APP_DOWNLOAD_SIZE}}" not in homepage
    instructions = httpx.get(f"{site_url}/downloads/READ-ME-FIRST.txt").text
    assert "_internal" in instructions and "ProducerOS.exe" in instructions
    assert httpx.get(f"{site_url}/downloads/produceros.db").status_code == 404


def test_deployment_archive_contains_only_intended_public_files():
    import zipfile

    manifest = json.loads(
        (ROOT / "release-artifacts/prodos-site-20260910.manifest.json").read_text()
    )
    archive = ROOT / "release-artifacts" / manifest["archive"]
    with archive.open("rb") as handle:
        assert hashlib.file_digest(handle, "sha256").hexdigest() == manifest["sha256"]
    with zipfile.ZipFile(archive) as deploy:
        names = deploy.namelist()
        assert "index.html" in names and ".htaccess" in names
        assert "downloads/ProducerOS-0.2.1-Windows.zip" in names
        assert set(names) == set(manifest["files"])
        assert not any(
            name.startswith(("src/", ".work/", "tests/", "migrations/"))
            or name.endswith((".db", ".key", ".py", ".log"))
            for name in names
        )
        for name in names:
            assert hashlib.sha256(deploy.read(name)).hexdigest() == manifest["files"][name]


def test_demo_edits_are_isolated_resettable_and_ephemeral(browser, site_url):
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url))
    page.goto(site_url)
    expect(page.locator("#demo-stage")).to_have_value("master")
    page.locator('#demo-checklist input[name="rights"]').check()
    expect(page.locator("#readiness-progress")).to_have_js_property("value", 3)
    title = "<img src=x onerror=alert(1)> My next release"
    page.locator("#demo-title-input").fill(title)
    page.locator("#demo-stage").select_option("released")
    expect(page.locator("#demo-title")).to_have_text(title)
    expect(page.locator("#demo-title img")).to_have_count(0)
    page.locator('button[data-project="tide"]').click()
    expect(page.locator("#readiness-progress")).to_have_js_property("value", 0)
    expect(page.locator("#demo-stage")).to_have_value("production")
    page.locator('button[data-project="horizon"]').click()
    expect(page.locator("#demo-stage")).to_have_value("released")
    expect(page.locator("#demo-title-input")).to_have_value(title)
    expect(page.locator("#readiness-progress")).to_have_js_property("value", 3)
    page.locator("#demo-reset").click()
    expect(page.locator("#demo-title-input")).to_have_value("Glass Horizon")
    expect(page.locator("#readiness-progress")).to_have_js_property("value", 2)
    page.locator("#demo-title-input").fill("A temporary change")
    page.reload()
    expect(page.locator("#demo-title-input")).to_have_value("Glass Horizon")
    assert (
        page.evaluate("Object.keys(localStorage).length + Object.keys(sessionStorage).length") == 0
    )
    assert context.cookies() == []
    assert all(url.startswith(site_url + "/") for url in requests)
    assert errors == []
    context.close()


def test_audio_plays_seeks_and_resets(browser, site_url):
    context = browser.new_context()
    page = context.new_page()
    page.goto(site_url)
    audio = page.locator("#demo-audio")
    audio.evaluate("element => element.play()")
    expect(audio).to_have_js_property("paused", False)
    assert 17 < audio.evaluate("element => element.duration") < 18
    audio.evaluate("element => { element.currentTime = 8; }")
    expect(audio).to_have_js_property("seeking", False)
    assert audio.evaluate("element => element.currentTime") >= 8
    page.locator("#demo-reset").click()
    expect(audio).to_have_js_property("paused", True)
    expect(audio).to_have_js_property("currentTime", 0)
    context.close()


@pytest.mark.parametrize("width", [360, 390, 768, 1440])
def test_layout_and_real_download(browser, site_url, width, tmp_path):
    context = browser.new_context(viewport={"width": width, "height": 900}, accept_downloads=True)
    page = context.new_page()
    page.goto(site_url)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator('button[data-project="lanterns"]').click()
    expect(page.locator("#demo-title")).to_have_text("Paper Lanterns")
    page.locator("#demo-title-input").fill("My producer demo project")
    page.locator('#demo-checklist input[name="master"]').check()
    expect(page.locator("#readiness-progress")).to_have_js_property("value", 2)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if width == 1440:
        with page.expect_download() as pending:
            page.get_by_role("link", name="Download ProducerOS", exact=True).click()
        downloaded = tmp_path / pending.value.suggested_filename
        pending.value.save_as(downloaded)
        with downloaded.open("rb") as handle:
            assert (
                hashlib.file_digest(handle, "sha256").hexdigest()
                == json.loads((BUILT / "release.json").read_text())["sha256"]
            )
    else:
        expect(page.get_by_role("link", name="Download ProducerOS", exact=True)).to_be_visible()
    context.close()


def test_no_javascript_keeps_guidance_links_and_faq_usable(browser, site_url):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(site_url)
    expect(page.locator("#demo-title-input")).to_be_disabled()
    expect(page.get_by_role("link", name="Download ProducerOS", exact=True)).to_have_attribute(
        "href", "downloads/ProducerOS-0.2.1-Windows.zip"
    )
    page.locator("summary").filter(has_text="Does my music get uploaded?").click()
    expect(page.locator("details[open] p")).to_contain_text("references music files")
    assert httpx.get(f"{site_url}/downloads/SHA256SUMS.txt").text.startswith(
        json.loads((BUILT / "release.json").read_text())["sha256"]
    )
    expect(page.locator("#share-link")).to_have_value("https://prodos.tech/")
    context.close()


def test_share_control_has_a_visible_fallback(browser, site_url):
    context = browser.new_context()
    context.add_init_script("""
        Object.defineProperty(navigator, 'share', {value: undefined});
        Object.defineProperty(navigator, 'clipboard', {value: undefined});
    """)
    page = context.new_page()
    page.goto(site_url)
    page.locator("#share-button").click()
    expect(page.locator("#share-link")).to_be_focused()
    expect(page.locator("#share-status")).to_contain_text("Select and copy")
    context.close()
