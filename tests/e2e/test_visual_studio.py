"""Real browser checks for the redesigned studio and previously blocked controls."""

import re
import time

from playwright.sync_api import expect

from produceros.demo.audio_fixtures import generate_sine_wav
from tests.e2e.test_full_workflow import _complete_setup


def test_player_mobile_assets_backup_and_offline_shell(make_page, live_server, tmp_path):
    page = make_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _complete_setup(page, live_server)
    page.goto(f"{live_server}/projects/new")
    page.fill("#working_title", "Studio regression")
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r".*/projects/[0-9a-f-]{36}$"))
    project_url = page.url
    music = tmp_path / "music"
    tone = generate_sine_wav(music / "test-preview.wav", seconds=12)
    page.fill("#project_root_path", str(music))
    page.fill("#tags", "summer, driving")
    page.check("#split_confirmed")
    page.click("#overview button[type=submit]")
    expect(page.locator("#tags")).to_have_value(re.compile("summer|driving"))
    expect(page.locator("#split_confirmed")).to_be_checked()
    page.uncheck("#split_confirmed")
    page.click("#overview button[type=submit]")
    expect(page.locator("#split_confirmed")).not_to_be_checked()
    assert set(page.locator("#tags").input_value().split(", ")) == {"summer", "driving"}

    page.select_option("#asset_type", label="Master")
    page.fill("#file_path", str(tone))
    page.click("#assets button[type=submit]")
    expect(page.get_by_role("button", name="Play audio preview")).to_be_visible()
    page.get_by_role("button", name="Play audio preview").click()
    deadline = time.monotonic() + 5
    while (
        page.locator("audio").evaluate("a => a.currentTime") <= 0.1 and time.monotonic() < deadline
    ):
        time.sleep(0.05)
    assert page.locator("audio").evaluate("a => a.currentTime") > 0.1
    assert page.locator("audio").evaluate("a => a.duration") == 12
    page.get_by_role("button", name="Pause audio preview").click()
    assert page.locator("audio").evaluate("a => a.paused")

    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(project_url + "#assets")
    expect(page.locator("#assets table")).to_be_visible()
    expect(
        page.locator("#assets").get_by_role("cell", name="test-preview.wav", exact=True)
    ).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.goto(f"{live_server}/projects")
    page.get_by_role("button", name="Filters", exact=True).click()
    expect(page.locator("[data-filter-drawer]")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("[data-filter-drawer]")).not_to_be_visible()
    expect(page.get_by_role("button", name="Filters", exact=True)).to_be_focused()

    page.goto(f"{live_server}/backup")
    page.get_by_role("button", name="Create backup now").click()
    page.get_by_role("button", name="Restore dry run", exact=True).click()
    expect(page.locator(".dry-run-result")).to_contain_text("Backup is valid")
    expect(page.locator(".dry-run-result")).to_be_visible()

    page.goto(f"{live_server}/analytics")
    page.select_option("#project_id", label="Studio regression")
    page.get_by_role("button", name="Show analytics").click()
    page.wait_for_url(re.compile(r".*/analytics\?project_id=.+"))
    page.goto(live_server)
    page.goto(f"{live_server}/offline.html")
    expect(page.locator("#last-summary")).to_be_visible()
    expect(page.locator("#last-summary")).to_contain_text("Studio regression")
    page.get_by_role("button", name="Try again").click()
    page.wait_for_url(live_server + "/")
    assert not errors


def test_mobile_project_filters_work_without_javascript(browser, live_server):
    context = browser.new_context(java_script_enabled=False, viewport={"width": 375, "height": 812})
    page = context.new_page()
    try:
        _complete_setup(page, live_server)
        page.goto(f"{live_server}/projects")
        expect(page.locator("#search")).to_be_visible()
        page.fill("#search", "no match")
        page.get_by_role("button", name="Apply", exact=True).click()
        page.wait_for_url(re.compile(r".*/projects\?search=no\+match.*"))
    finally:
        context.close()
