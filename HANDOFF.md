# HANDOFF

Current state of ProducerOS for whoever works on it next. Keep this
document updated whenever project state changes materially -- it is
required to be current (spec `docs/PRODUCT_SPEC.md`, section 33).

Last updated: 2026-07-20.

## Where things stand

The initial build is **complete**: application core, web app/PWA,
security, MCP server, demo mode, four test suites, a real Windows
installer (not just a portable zip), CI/CD workflows, and the full
documentation set. Development happened on branch
`claude/prodos-backend-pwa-dashboard-hsmaeo` (earlier history also exists
on `claude/prodos-music-management-pv70iy`, which this branch
fast-forwarded from -- treat the `hsmaeo` branch as canonical).

**Latest addition**: a proper installer experience, since the actual goal
is "a non-technical friend downloads it, double-clicks it, gets a desktop
icon, and uses that icon from then on." See
[ADR 0006](docs/adr/0006-inno-setup-installer.md) for the full design:
Inno Setup, per-user install (no admin/UAC prompt), Start Menu + desktop
shortcuts, upgrade-in-place via a fixed `AppId`, windowed (no console)
PyInstaller build with a real embedded `.ico`, and a post-uninstall
message confirming user data was kept. `scripts/build_installer.ps1`
builds it; `.github/workflows/windows-build.yml` now silent-installs the
compiled installer, verifies both shortcuts exist, launches the
*installed* exe, and silently uninstalls it to confirm data survives.

## What is verified vs. not

**Verified by actually running it** (Linux dev container, Python 3.12):

- Full test suite passing: unit + integration + security
  (`pytest tests/unit tests/integration tests/security -q`) and
  Playwright e2e (`pytest tests/e2e -q`) -- exact counts in the CI logs
  and the final build report; one unit test self-skips when running as
  root (file-permission simulation impossible).
- `ruff format --check`, `ruff check`, `mypy src` on the shipped code.
- `alembic check` -- migrations match models, no drift.
- Demo data load -> clean round trip.
- A PyInstaller build **of a Linux binary from the same spec file**,
  smoke-tested end-to-end: migrations apply, server serves 200s, every
  CLI subcommand works, argv forwarding works.
- MCP server actually starting alongside the web app when enabled (both
  ports responding).
- Mobile layout in a real Chromium at phone viewports, portrait and
  landscape (`tests/e2e/test_mobile_viewport.py`).

**Not verified** (no Windows machine, no Inno Setup, no CI minutes
available in the build environment):

- A real Windows `.exe` and the real Inno Setup installer -- neither has
  been built or run on real Windows. `windows-build.yml` builds the
  installer, silent-installs it, checks both shortcuts exist, launches
  the installed exe, and silently uninstalls it to confirm
  `%LOCALAPPDATA%\ProducerOS\` survives -- but that workflow has **never
  been triggered**. Same for `ci.yml`, `security.yml`, and `release.yml`:
  written, YAML-validated, unexecuted. **First priority for the next
  session**: push to a branch/PR that triggers them and fix whatever
  surfaces -- the `.iss` script in particular has only been manually
  reviewed against Inno Setup's documented syntax, never compiled.
- A real Android device installing the PWA over LAN (mobile support was
  verified via Chromium viewport emulation, not physical hardware).
- An external MCP client (e.g. Claude Desktop) driving the MCP tools
  end-to-end.
- Whether Windows SmartScreen's warning on the unsigned installer is as
  mild as documented (`docs/INSTALL_WINDOWS.md` describes "More info ->
  Run anyway") -- this is standard behavior for unsigned installers but
  hasn't been seen firsthand here.

## Gotchas the hard-won way (do not rediscover)

1. **`\b` regex boundaries fail next to underscores** (word chars). Use
   `(?<![A-Za-z0-9])` / `(?![A-Za-z0-9])` -- see
   `scanners/filename_parser.py`.
2. **FastAPI discards `response.set_cookie()` on injected `Response`
   params** when the route returns its own response. All cookie issuance
   goes through middleware in `web/app.py`; follow that pattern for new
   form routes (`docs/SECURITY_MODEL.md`).
3. **SQLite loses tzinfo** on `DateTime(timezone=True)` columns; always
   use `UTCDateTime` from `db/base.py` (ADR 0004).
4. **PyInstaller 6 puts bundled `datas` under `_internal/`**, not next to
   the exe; resolve via `sys._MEIPASS` when frozen (ADR 0005). And the
   frozen launcher must forward argv -- both were real bugs.
5. **`.record-card` vs `.record-card-mobile-only`** in `app.css`: only
   the latter is hidden on desktop. Pages that render a desktop table AND
   mobile cards use the `-mobile-only` variant; everything else uses
   plain `.record-card` (this distinction exists because the original
   single class hid most desktop lists entirely).
6. **`qrcode` without Pillow** falls back to `PyPNGImage`, whose
   `.save()` rejects `format=` -- `services/network.qr_code_data_uri`
   handles both backends.
7. **Demo cleanup order matters**: `demo/generator.py` tracks a manifest
   deleted in reverse order; parents must be `track()`-ed before
   children. Re-verify load->clean round trip after touching it.
8. **Bash-tool cwd persists** in agent sessions: a `cd` into
   `web/routes/` once shadowed stdlib `calendar` via `sys.path[0]`. Run
   Python/pytest from the repo root.
9. **Playwright: never pair `click` + `wait_for_load_state("networkidle")`
   + an instant `is_visible()` assert after a form submit.** The
   networkidle wait can resolve *before* the 303-redirect navigation
   starts (the pre-submit page is already idle), so the assert runs
   against the stale DOM and flakes -- this was diagnosed from server
   access logs showing the POST/redirect succeeding while the assert
   failed. All post-submit assertions in `tests/e2e/` use polling
   `expect(...)` instead; keep it that way for new e2e steps. The
   `live_server` fixture keeps uvicorn access logs on precisely so the
   next such flake is diagnosable from the pytest failure output.
10. **A second, different e2e flake mode exists in *this specific sandboxed
   dev container*, unrelated to #9's fix**: running the full combined
   suite (`tests/unit tests/integration tests/security tests/e2e`)
   back-to-back occasionally times out on the very first `page.click()` +
   `wait_for_url()` in `_complete_setup()`, with the access log showing
   the `POST /setup` *never arriving* at the server at all (only the
   preceding `GET` requests logged) -- a 60-second client-side stall, not
   a server-side race. That's this container's CPU/IO getting
   oversubscribed when several heavy processes (multiple SQLite-backed
   pytest sessions, a live uvicorn server, a real Chromium instance) stack
   without settling time, not an application or test-logic bug: `pytest
   tests/e2e -q` alone was rerun clean (4/4) three separate times in this
   session, including immediately after a full-suite run that hit this.
   If it recurs on real CI (`windows-latest`/`ubuntu-latest` dedicated
   runners, not a shared sandbox), it's far less likely given real
   per-job CPU allocation, but if it does: consider running `tests/e2e` as
   its own CI job/step with nothing else concurrent, or raising
   `EXPECT_TIMEOUT_MS`/`make_page`'s navigation timeout further, before
   assuming it's a real regression.
11. **A windowed PyInstaller build (`console=False`) gets `sys.stdout`/
    `sys.stderr = None`** from Windows -- no console exists to attach
    them to. Any bare `print()` or the logging module's default
    `StreamHandler` crashes on the very first line without
    `launcher.py`'s `_fix_windowed_stdio()`, which must run before any
    other import. If you ever see this fixed differently (e.g. per-call
    `if sys.stdout:` guards scattered around), prefer reverting to the
    single fix-at-entry-point approach -- it's one place to get right
    instead of every call site.
12. **The install directory and the data directory must never be the same
    path.** The installer installs to `%LOCALAPPDATA%\Programs\ProducerOS`;
    app data lives at `%LOCALAPPDATA%\ProducerOS`. This is what makes
    upgrade (`[InstallDelete]` wiping `_internal\`) and uninstall
    completely safe with zero special-case code -- don't "simplify" this
    by installing to the same tree as the data dir.
13. **The Inno Setup `AppId` GUID in `packaging/inno/producer-os.iss`
    must never change.** It's what makes a newer installer register as
    an upgrade instead of a second, parallel install. If it's ever
    accidentally regenerated, every existing user's install becomes
    stranded (their old copy stays installed and unrelated to the new
    one) -- treat it like a permanent, immutable identifier.

## Environment quick-start (dev container)

```bash
cd /home/user/ProdOS
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" httpx
pytest tests/unit tests/integration tests/security -q
# e2e: Chromium is pre-installed at /opt/pw-browsers/chromium
#      (tests/e2e/conftest.py already points at it; never run
#      `playwright install`)
pytest tests/e2e -q
```

## Suggested next steps, in order

1. Trigger the GitHub Actions workflows (open a PR or push to main per
   their `on:` blocks); fix anything that only surfaces on real
   `windows-latest` (most likely candidates: the `.iss` script failing to
   compile for a syntax reason invisible to manual review, PowerShell
   quirks in `windows-build.yml`'s installer smoke test, Playwright
   browser install timing in `ci.yml`).
2. Tag `v0.1.0` once CI is green to exercise `release.yml` end-to-end and
   produce a real, downloadable `ProducerOS-Setup-0.1.0.exe`.
3. Actually install that on a real Windows machine once: confirm the
   SmartScreen warning reads the way `docs/INSTALL_WINDOWS.md` describes,
   confirm the desktop icon looks right (the generated `.ico`'s visual
   correctness was only checked as a rendered PNG frame here, never as an
   actual Windows shortcut icon), and confirm a second run of the
   installer genuinely upgrades rather than duplicating.
4. Verify on a real Android phone: LAN pairing walkthrough in
   `docs/ANDROID_PWA.md`, PWA install, revocation.
5. Point a real MCP client at the MCP server and exercise the 14 tools.
6. Then the roadmap (`ROADMAP.md`) -- audit-log page and in-app scheduled
   backups are the highest-leverage small items.
