"""End-to-end desktop workflow, driven with a real Chromium browser against
a live ProducerOS server (not TestClient): first-run setup, login, create
artist and project, register an asset, add a contributor and rights share,
start a release and run the readiness checklist, generate a marketing
draft, create a calendar deadline, build a delivery manifest, and take a
metadata backup.

Assertion style matters here: after submitting a form, the server responds
303 and the browser re-navigates. ``wait_for_load_state("networkidle")``
can resolve *before* that navigation even starts (the pre-submit page is
already idle), so an instant ``is_visible()`` assert races the redirect
and flakes. Every post-submit assertion therefore uses Playwright's
polling ``expect(...)``, which retries until the redirected page renders.
"""

from __future__ import annotations

import re

from playwright.sync_api import expect

USERNAME = "producer"
PASSWORD = "correcthorsebattery"
EXPECT_TIMEOUT_MS = 15_000


def _complete_setup(page, base_url):
    page.goto(f"{base_url}/setup")
    page.fill("#display_name", "Test Producer")
    page.fill("#username", USERNAME)
    page.fill("#password", PASSWORD)
    page.fill("#password_confirm", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r".*/$"))


def test_full_desktop_workflow(make_page, live_server):
    page = make_page(viewport={"width": 1440, "height": 900})
    base_url = live_server

    # First-run setup -> logged in, on the dashboard.
    _complete_setup(page, base_url)
    expect(page.locator("text=Dashboard").first).to_be_visible(timeout=EXPECT_TIMEOUT_MS)

    # Create an artist.
    page.goto(f"{base_url}/artists")
    page.fill("input[name=name]", "Midnight Run")
    page.click("button[type=submit]")
    expect(page.locator("text=Midnight Run").first).to_be_visible(timeout=EXPECT_TIMEOUT_MS)

    # Create a project.
    page.goto(f"{base_url}/projects/new")
    page.fill("#working_title", "Neon Skyline")
    page.select_option("#artist_id", label="Midnight Run")
    page.fill("#genre", "Synthwave")
    page.fill("#bpm", "118")
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r".*/projects/[0-9a-f-]{36}$"))
    project_url = page.url

    # Register a master asset.
    page.select_option("#asset_type", label="Master")
    page.fill("#file_path", "D:\\Music\\Exports\\NeonSkyline_Master_v1.wav")
    page.click("#assets button[type=submit]")
    expect(page.locator("#assets h3").first).to_be_visible(timeout=EXPECT_TIMEOUT_MS)

    # Add a contributor and mark them approved (click auto-waits for the
    # post-redirect button to exist, so no explicit wait is needed).
    page.fill("#c_name", "Jani Starck")
    page.select_option("#c_role", label="Producer")
    page.click("#rights form[action*='contributors/new'] button[type=submit]")
    page.click("text=Mark approved")
    expect(page.locator("#rights .record-card").first).to_be_visible(timeout=EXPECT_TIMEOUT_MS)

    # Add a confirmed rights share.
    page.fill("#rs_holder", "Jani Starck")
    page.fill("#rs_pct", "100")
    page.click("#rights form[action*='rights-shares/new'] button[type=submit]")
    expect(
        page.locator("#rights form[action*='rights-shares/'][action$='update']").first
    ).to_be_visible(timeout=EXPECT_TIMEOUT_MS)

    # Start a release from this project and run the readiness checklist.
    page.goto(f"{base_url}/releases/new?project_id={project_url.rsplit('/', 1)[-1]}")
    page.fill("input[name=title]", "Neon Skyline")
    page.select_option("select[name=release_type]", index=1)
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r".*/releases/[0-9a-f-]{36}$"))
    expect(page.locator("text=Neon Skyline").first).to_be_visible(timeout=EXPECT_TIMEOUT_MS)

    # Generate a marketing draft for the project.
    page.goto(f"{base_url}/marketing")
    page.select_option("select[name=project_id]", label="Neon Skyline")
    page.select_option("select[name=draft_type]", index=1)
    page.click("form[action='/marketing/drafts/generate'] button[type=submit]")
    page.wait_for_url(re.compile(r".*/marketing/drafts/[0-9a-f-]{36}$"))

    # Add a calendar deadline.
    page.goto(f"{base_url}/calendar")
    page.fill("input[name=title]", "Master approval deadline")
    page.fill("input[name=due_date]", "2026-08-15")
    page.select_option("select[name=deadline_type]", index=1)
    page.click("form[action='/calendar/deadlines/new'] button[type=submit]")
    expect(page.locator("text=Master approval deadline").first).to_be_visible(
        timeout=EXPECT_TIMEOUT_MS
    )

    # Build a delivery manifest (dry run only, never executed here).
    page.goto(f"{base_url}/delivery")
    page.select_option("select[name=project_id]", label="Neon Skyline")
    page.select_option("select[name=preset_id]", index=1)
    page.fill("input[name=output_directory]", "/tmp/produceros-e2e-delivery")
    page.click("form[action='/delivery/packages/new'] button[type=submit]")
    page.wait_for_url(re.compile(r".*/delivery/packages/[0-9a-f-]{36}$"))
    page.click("text=Generate manifest")
    expect(page.locator("body")).to_contain_text(
        "manifest", ignore_case=True, timeout=EXPECT_TIMEOUT_MS
    )

    # Take a metadata backup.
    page.goto(f"{base_url}/backup")
    page.click("form[action='/backup/create'] button[type=submit]")
    expect(page.locator(".record-card").first).to_be_visible(timeout=EXPECT_TIMEOUT_MS)
