# Screenshots

Real screenshots captured with Playwright/Chromium against a live
ProducerOS instance loaded with the synthetic demo dataset
(`produceros demo-load`), the same infrastructure `tests/e2e/` uses --
not mockups.

- `dashboard-desktop.png` -- dashboard at a 1440x900 desktop viewport
  (sidebar navigation).
- `projects-list-desktop.png` -- the projects list.
- `project-detail-desktop.png` -- a single project's detail page.
- `dashboard-mobile.png` -- dashboard at a 375x667 mobile viewport
  (bottom tab navigation, per `docs/ANDROID_PWA.md`).

These are a small, representative set, not full page-by-page coverage.
To regenerate or add more, see the screenshot-capture approach in
`tests/e2e/conftest.py`'s `live_server`/`browser` fixtures -- drive the
live server with `playwright.sync_api` and call `page.screenshot(path=...)`.
