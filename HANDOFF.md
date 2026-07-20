# HANDOFF

Current state of ProducerOS for whoever works on it next. Keep this
document updated whenever project state changes materially -- it is
required to be current (spec `docs/PRODUCT_SPEC.md`, section 33).

Last updated: 2026-07-19.

## Where things stand

The initial build is **complete**: application core, web app/PWA,
security, MCP server, demo mode, four test suites, Windows packaging
config, CI/CD workflows, and the full documentation set. Development
happened on branch `claude/prodos-backend-pwa-dashboard-hsmaeo`
(earlier history also exists on `claude/prodos-music-management-pv70iy`,
which this branch fast-forwarded from -- treat the `hsmaeo` branch as
canonical).

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

**Not verified** (no Windows machine or CI minutes available in the build
environment):

- A real Windows `.exe` -- `windows-build.yml` builds and smoke-tests one
  on `windows-latest`, but that workflow has **never been triggered**.
  Same for `ci.yml`, `security.yml`, and `release.yml`: written,
  YAML-validated, unexecuted. First priority for the next session: push
  to a branch/PR that triggers them and fix whatever surfaces.
- A real Android device installing the PWA over LAN (mobile support was
  verified via Chromium viewport emulation, not physical hardware).
- An external MCP client (e.g. Claude Desktop) driving the MCP tools
  end-to-end.

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
   `windows-latest` (most likely candidates: PowerShell quirks in
   `windows-build.yml`'s smoke test, Playwright browser install timing in
   `ci.yml`).
2. Tag `v0.1.0` once CI is green to exercise `release.yml` end-to-end.
3. Verify on a real Android phone: LAN pairing walkthrough in
   `docs/ANDROID_PWA.md`, PWA install, revocation.
4. Point a real MCP client at the MCP server and exercise the 14 tools.
5. Then the roadmap (`ROADMAP.md`) -- audit-log page and in-app scheduled
   backups are the highest-leverage small items.
