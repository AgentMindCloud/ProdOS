# Agent / Contributor Rules

Permanent rules for anyone (human or AI) working on this repository, per
`docs/PRODUCT_SPEC.md` section 5. These are non-negotiable constraints on
ProducerOS's behavior, not style preferences -- if a change would violate
one of these, stop and reconsider the approach rather than working around
it.

## Zero external dependencies at runtime

ProducerOS must work with **no external API keys, no cloud services, no
Docker, and no internet access after install**. Every runtime web asset
(CSS, JS, fonts, icons) is generated at build time or stored in the repo
-- never loaded from a CDN. Do not add a feature that requires any of
these, even optionally, without treating it as a significant scope change
that needs explicit sign-off.

## Never touch music files without explicit approval

ProducerOS must never delete, rename, move, or overwrite a music file on
disk on its own initiative. Every file-management action starts as a
dry run and requires an explicit approval step before it touches disk
(`services/file_operations.py`). The scanner (`scanners/engine.py`) is
read-only, full stop -- it only ever produces `ScannerFinding` rows, never
mutates a file. See `docs/SECURITY_MODEL.md`.

Never interpret or reverse-engineer `.flp` (FL Studio project) file
internals -- ProducerOS only records metadata *about* a project file's
path, never parses its contents.

## No AI-generated or invented marketing content

Marketing templates (`marketing/templates.py`) are local, deterministic,
and must never invent streaming numbers, awards, press mentions, credits,
or claims that a track "will be successful." `marketing/llm_provider.py`
exists as a disabled stub matching the original spec and must remain
disabled -- do not wire it up without an explicit, separate decision to
change this constraint.

## No automatic publishing or outbound messages

ProducerOS never publishes a release, sends an email, posts to social
media, or otherwise communicates on the producer's behalf. Draft
generation is always draft-only, reviewed and sent/used by the human.

## Rights percentages are never auto-corrected

`services/rights.py` validates that rights-share totals sum to 100% and
surfaces a warning when they don't, but never silently adjusts a
percentage. Any change to a rights share must be an explicit user action.

## Passwords and secrets

Never store a password in plaintext (`security.hash_password` via
Argon2). Never commit a secret key, session token, or real credential to
the repository. The session-signing secret key is generated once at
runtime and stored in the user's data directory, never in-repo. Logs must
redact anything secret-shaped before being written
(`logging_config.redact_secrets`) -- if you add a new kind of secret,
add a redaction pattern for it and a test.

## Not exposed publicly by default

ProducerOS binds to `127.0.0.1` unless the user explicitly chooses LAN
mode, and LAN mode is documented as "never forward this port through your
router." Do not change this default.

## The repository is the sole source of truth

Do not rely on undocumented local files, chat history, developer-specific
paths, developer-specific secrets, external databases, cloud storage,
manually installed JavaScript packages, or CDN-hosted scripts/fonts/CSS.
Everything ProducerOS needs to build and run must be reconstructable from
a fresh clone of this repository.

## Testing and honesty

Never claim a test passed without having actually run it. Never claim
mobile support, Windows packaging, or a security property without having
actually verified it (a real test, a real build, a real browser session)
-- if something wasn't verified, say so explicitly rather than assuming
it works. This has been true of every claim in `docs/` and commit
messages so far in this project's history; keep it that way.

## Where the rest of the rules live

- `docs/PRODUCT_SPEC.md` -- the full original specification.
- `docs/SECURITY_MODEL.md` -- the concrete security implementation.
- `docs/adr/` -- why specific architectural decisions were made.
- `CONTRIBUTING.md` -- day-to-day development workflow.
