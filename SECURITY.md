# Security Policy

## Reporting a vulnerability

Open a GitHub issue **without** exploit details and ask for a private
channel, or use GitHub's private vulnerability reporting on this
repository if enabled. Please don't publish working exploits before a fix
exists.

Include: ProducerOS version/commit, what an attacker can do, and
reproduction steps. Log excerpts are safe to attach -- secrets are
redacted before they're written (`docs/SECURITY_MODEL.md`).

## Scope

ProducerOS is a single-user, local-first application. In scope:

- Anything reachable by another device on the same LAN (LAN mode,
  pairing, device sessions).
- Anything that lets a request bypass login, CSRF, or the approval gate
  on file operations.
- Path traversal / symlink escapes past the configured scanner roots.
- Secrets leaking into logs, backups, exports, or the repository.

Out of scope (by design -- see `docs/SECURITY_MODEL.md`): multi-user
isolation, a hostile local machine, and public-internet exposure
(ProducerOS binds to localhost by default and LAN mode is documented as
home-network-only, never port-forwarded).

## Existing hardening

Argon2 password hashing, login lockout, signed session cookies with
timestamp-based revocation, double-submit CSRF, strict security headers +
CSP, rate-limited LAN pairing with hashed single-use codes, read-only
scanner with approval-gated file operations, argv-only subprocess calls,
and log redaction -- each covered by `tests/security/`. CI runs
`pip-audit`, `gitleaks`, and `bandit` on every push
(`.github/workflows/security.yml`).
