"""Mobile-viewport checks against a real live server: the bottom nav must
be visible below the 768px breakpoint (desktop sidebar hidden instead),
and the page must never scroll horizontally, in both portrait and
landscape -- this is exercised for real rather than assumed, per the
spec's mobile-support requirement."""

from __future__ import annotations

import re

import pytest

USERNAME = "producer"
PASSWORD = "correcthorsebattery"

# The app's responsive breakpoint is 768px width (mobile bottom nav below
# it, desktop sidebar at/above it), by design -- not orientation. A modern
# phone in landscape is often *wider* than 768px (e.g. a Pixel 7 is
# 915x412 landscape), so it intentionally gets the roomier desktop
# sidebar layout there. iPhone SE stays under the breakpoint in both
# orientations, so it's the realistic device to exercise "true mobile
# layout in both orientations" against.
PORTRAIT = {"width": 375, "height": 667}
LANDSCAPE = {"width": 667, "height": 375}


def _complete_setup(page, base_url):
    page.goto(f"{base_url}/setup")
    page.fill("#display_name", "Test Producer")
    page.fill("#username", USERNAME)
    page.fill("#password", PASSWORD)
    page.fill("#password_confirm", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_url(re.compile(r".*/$"))


def _no_horizontal_scroll(page) -> bool:
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


@pytest.mark.parametrize("viewport,orientation", [(PORTRAIT, "portrait"), (LANDSCAPE, "landscape")])
def test_bottom_nav_visible_and_no_horizontal_scroll(make_page, live_server, viewport, orientation):
    page = make_page(viewport=viewport)
    base_url = live_server
    _complete_setup(page, base_url)

    for path in ("/", "/projects", "/releases", "/calendar"):
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("networkidle")

        bottom_nav = page.locator("nav.bottom-nav")
        assert bottom_nav.is_visible(), f"bottom nav should be visible on {path} in {orientation}"

        sidebar = page.locator("nav.sidebar")
        assert (
            not sidebar.is_visible()
        ), f"desktop sidebar should be hidden on {path} in {orientation}"

        assert _no_horizontal_scroll(page), f"{path} scrolls horizontally in {orientation}"


def test_wide_landscape_phone_gets_desktop_sidebar_by_design(make_page, live_server):
    """A phone whose landscape width crosses the 768px breakpoint (e.g. a
    Pixel 7 at 915x412) intentionally gets the desktop sidebar rather than
    the bottom nav -- the breakpoint is width-based, not orientation-based."""
    page = make_page(viewport={"width": 915, "height": 412})
    base_url = live_server
    _complete_setup(page, base_url)
    page.wait_for_load_state("networkidle")

    assert page.locator("nav.sidebar").is_visible()
    assert not page.locator("nav.bottom-nav").is_visible()
    assert _no_horizontal_scroll(page)
