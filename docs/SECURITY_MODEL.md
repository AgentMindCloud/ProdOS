# Security Model

ProducerOS is a single-user, local-first application. Its security model
is designed around one threat that actually matters for that shape of
app: someone else on the same network (or a compromised script on the
same machine) reaching the app or the producer's files. It is not
designed for multi-tenant isolation.

## Authentication

- One admin account (`User`), created during first-run `/setup`. Password
  hashed with Argon2 (`argon2-cffi`, `security.hash_password` /
  `verify_password`), never stored or logged in plaintext.
- Login sessions are signed cookies, not server-side session rows -- see
  [ADR 0003](adr/0003-signed-cookies-not-server-side-sessions.md) for the
  full rationale, including how "logout everywhere" works without a
  session table (`services/auth.invalidate_all_sessions`, a per-user
  `session_invalidated_before` timestamp checked on every request).
- Brute-force protection: 5 failed logins locks the account for 60
  seconds (`services/auth.LOGIN_LOCKOUT_THRESHOLD` /
  `LOGIN_LOCKOUT_SECONDS`). Verified end-to-end in
  `tests/security/test_auth_security.py`.

## CSRF

Double-submit cookie pattern (`web/csrf.py`): a random token is stored in
an httponly cookie and rendered into every form as a hidden field; a POST
must present the same value. Because the cookie is httponly, a
cross-site attacker's forged form can't read it to produce a matching
hidden field.

**Implementation gotcha, worth knowing before touching this code:** a
route's `response: Response` FastAPI dependency parameter's
`set_cookie()` calls are silently discarded whenever the route returns
its own `Response` object (e.g. a `TemplateResponse` or `RedirectResponse`)
instead of mutating the injected one. The CSRF cookie is therefore issued
by a single `csrf_cookie_middleware` in `web/app.py`, which sets
`request.state.csrf_token` before the route runs and attaches the
`Set-Cookie` header to whatever response the route actually returns.
Routes read the token via `web.csrf.get_csrf_token(request)`; they never
try to set the cookie themselves. Any new form-rendering route should
follow this pattern.

## File-system safety

ProducerOS never deletes, renames, moves, or overwrites a file on disk on
its own initiative:

- The scanner (`scanners/engine.py`) is read-only. It only records
  `ScannerFinding` rows.
- Turning a finding into a real file change always goes through
  `services/file_operations.py`: `propose_operation` (creates a
  `PENDING_APPROVAL`, `dry_run=True` row) -> `approve_operation` -> only
  then `execute_operation`.
- `execute_operation` re-validates the source/destination paths against
  the configured scanner roots (`security.resolve_within_allowed_roots`)
  **even if the operation was somehow already approved**, refuses to
  overwrite an existing destination file, and refuses `REPLACE` outright
  -- ProducerOS never overwrites an existing music file, full stop. See
  `tests/security/test_file_operations_security.py`.
- `resolve_within_allowed_roots` (`security.py`) rejects path traversal
  (`..`) and symlink escapes by resolving the real path and checking it's
  still inside an allowed root -- covered by both unit tests
  (`tests/unit/test_security.py`) and the file-operations security suite.

## Command execution

FFmpeg/FFprobe (optional, auto-detected on PATH) are only ever invoked
with a fixed argument list (`subprocess.run([...])`), never `shell=True`
and never a string-built command line (`audio/ffmpeg.py`). A filename
containing shell metacharacters is passed through argv as a literal
string, not interpreted. Verified with an AST-level check plus a
functional check using a deliberately dangerous filename
(`tests/security/test_shell_injection.py`).

## LAN pairing (Android access)

LAN mode binds to the machine's private LAN address instead of
`127.0.0.1`; never forward this port through a router (enforced only by
documentation and a UI warning, not technically -- this is a local-network
feature by design). Pairing:

1. Desktop (already logged in) generates a short-lived (10-minute
   default), single-use pairing code plus a QR code, entirely offline
   (`qrcode`'s pure-Python PNG backend, no external QR service --
   `services/network.qr_code_data_uri`).
2. The phone submits the code to `/lan/pair/{device_id}/confirm`, which is
   intentionally **not** behind `require_login` (that's the whole point --
   a new phone has no session yet), but is rate-limited: 5 attempts/minute
   per IP by default (`services/pairing._check_rate_limit`), verified at
   both the service level (`tests/unit/test_pairing.py`) and the HTTP
   level (`tests/security/test_pairing_http.py`).
3. On success, the device gets its own signed cookie (a device ID, not a
   long-lived credential) and its `PairedDevice.status` becomes `ACTIVE`.
4. Revoking a device (`/settings/lan/devices/{id}/revoke`) sets its status
   to `REVOKED`; authorization is re-checked against the live database row
   on every request, so revocation takes effect on the device's very next
   request with no cookie denylist to maintain.

**Known limitation:** the pairing rate limiter is in-process
(`services/pairing._pairing_attempts`, a module-level dict) and resets on
app restart. Acceptable for a single-user local LAN feature -- it isn't
protecting a public-facing service -- but it means a restart during an
active brute-force attempt resets the attacker's counter too.

## Logging & secrets

- `logging_config.redact_secrets` strips anything matching a password,
  Authorization header, session token, pairing code, secret key, or CSRF
  token pattern before a log line reaches disk or stderr
  (`RedactionFilter`), so logs are always safe to share for
  troubleshooting. Verified in `tests/security/test_secret_redaction.py`,
  including a check that a real configured logger actually redacts on
  write, not just that the regex works in isolation.
- The session-signing secret key is generated once and stored in the data
  directory (`config.Settings.load_or_create_secret_key`), never in the
  repository, never logged.

## HTTP security headers

Every response gets `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a restrictive
`Permissions-Policy`, and a `Content-Security-Policy` that only allows
`'self'` for scripts/styles/fonts/connect and blocks framing entirely
(`security.SECURITY_HEADERS`, applied by `security_headers_middleware` in
`web/app.py`).

## MCP server

Off by default (`config.toml [mcp] enabled`), binds to localhost only
when enabled, and every tool call is audited (`mcp_server/server.py`'s
`_audited()` wrapper writes an `AuditEvent` before returning). See
`docs/MCP.md` for the full tool list and enable instructions, and
[ADR 0002](adr/0002-fastmcp-for-mcp-server.md) for why it's built on
FastMCP.

## What this model does *not* cover

Multi-user isolation, network-facing hardening beyond "don't forward the
port," and defense against a fully compromised host machine are out of
scope -- ProducerOS assumes the machine it runs on is trusted, per the
spec's single-producer, local-first design.
