## Summary

<!-- What changed and why. -->

## Test plan

- [ ] `ruff format --check src tests`
- [ ] `ruff check src tests`
- [ ] `mypy src`
- [ ] `pytest tests/unit tests/integration tests/security -q`
- [ ] `pytest tests/e2e -q` (if the change touches the web UI)
- [ ] `alembic check` (if the change touches models)

## Checklist

- [ ] No new external API keys, cloud services, or required internet access
- [ ] File operations stay dry-run-by-default / explicitly approved (`docs/SECURITY_MODEL.md`)
- [ ] No fabricated marketing claims, streaming numbers, or credits
- [ ] Docs updated if behavior changed (`docs/`, `HANDOFF.md`, `CHANGELOG.md`)
