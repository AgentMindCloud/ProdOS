# ADR 0003: Signed cookies instead of server-side session storage

## Status
Accepted

## Context
ProducerOS needs login sessions for the single producer account, plus a
separate, longer-lived credential for paired LAN devices (Android
phones). A conventional approach is a server-side session store (a
`sessions` table keyed by a random token, looked up on every request).
That requires a write on every login, a read on every request, and an
explicit row to delete on logout/expiry/revocation.

## Decision
Sessions are stateless, signed cookies (`itsdangerous.URLSafeTimedSerializer`,
`services/auth.issue_session_token` / `verify_session_token`), carrying the
user ID and issue timestamp, signed with a secret key generated once and
stored outside the repo in the data directory
(`config.Settings.load_or_create_secret_key`). LAN device sessions work
the same way (`services/pairing.issue_device_cookie_token` /
`resolve_device_from_cookie`), carrying a device ID instead of a user ID.

Because there's no session table to delete a row from, "logout" and
"revoke all sessions" are implemented as a per-user
`session_invalidated_before` timestamp stored in `AppSetting`
(`services/auth.invalidate_all_sessions`). Any cookie whose `issued_at` is
before that timestamp is rejected on verification, even though the
cookie's signature is still valid -- the same trick commonly used for
stateless JWT revocation. Device revocation is simpler: `PairedDevice.status`
is checked live on every request
(`services/pairing.resolve_device_from_cookie`), so setting it to
`REVOKED` takes effect on the device's very next request with no
denylist to maintain.

## Consequences
- No session table, no session-store cleanup job, no risk of a stale
  session row surviving a database restore that a signed-cookie approach
  wouldn't have anyway.
- Revocation is a single timestamp write (`session_invalidated_before`)
  instead of a session-table row delete -- functionally equivalent, but
  it also invalidates cookies the server never even knew existed (e.g. if
  a cookie were somehow copied to another browser before revocation).
- The secret key never lives in the repo (see `docs/SECURITY_MODEL.md`);
  losing it invalidates every outstanding session, which is the correct
  fail-safe behavior for a local single-user tool.
- This only works because ProducerOS has exactly one human account.
  Multi-user support would need per-session (not just per-user)
  revocation, which would push this back toward a server-side store --
  out of scope per the spec's single-producer design.
