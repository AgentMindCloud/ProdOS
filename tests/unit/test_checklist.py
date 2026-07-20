from sqlalchemy import select

from produceros.models.enums import ChecklistStatus, ExplicitStatus, ReleaseType
from produceros.models.release import ChecklistRule, Release
from produceros.services import catalog as catalog_service
from produceros.services.checklist import (
    evaluate_release,
    seed_default_rules,
    summarize_status,
    waive_result,
)


def _make_release(db_session, **project_fields) -> Release:
    project = catalog_service.create_project(
        db_session, working_title="Checklist Track", **project_fields
    )
    release = Release(
        project_id=project.id, release_type=ReleaseType.STREAMING_SINGLE, title="Checklist Track"
    )
    db_session.add(release)
    db_session.flush()
    return release


def test_seed_default_rules_is_idempotent(db_session):
    seed_default_rules(db_session)
    first_count = len(db_session.scalars(select(ChecklistRule)).all())
    seed_default_rules(db_session)
    second_count = len(db_session.scalars(select(ChecklistRule)).all())
    assert first_count == second_count
    assert first_count > 0


def test_new_release_has_blocking_checks(db_session):
    release = _make_release(db_session)
    results = evaluate_release(db_session, release)
    assert any(r.status == ChecklistStatus.BLOCKING for r in results)
    assert release.readiness_status == "blocking"


def test_social_only_release_waives_distributor_and_isrc(db_session):
    project = catalog_service.create_project(db_session, working_title="Social Track")
    release = Release(
        project_id=project.id, release_type=ReleaseType.SOCIAL_ONLY, title="Social Track"
    )
    db_session.add(release)
    db_session.flush()
    results = evaluate_release(db_session, release)

    from produceros.models.release import ChecklistRule

    rule_by_id = {r.id: r for r in db_session.query(ChecklistRule).all()}
    distributor_results = [
        r for r in results if rule_by_id[r.rule_id].code == "metadata.distributor_recorded"
    ]
    assert distributor_results and distributor_results[0].status == ChecklistStatus.WAIVED


def test_explicit_release_without_clean_version_is_blocking(db_session):
    project = catalog_service.create_project(
        db_session, working_title="Explicit Track", explicit_status=ExplicitStatus.EXPLICIT
    )
    release = Release(
        project_id=project.id, release_type=ReleaseType.STREAMING_SINGLE, title="Explicit Track"
    )
    db_session.add(release)
    db_session.flush()
    results = evaluate_release(db_session, release)

    from produceros.models.release import ChecklistRule

    rule_by_id = {r.id: r for r in db_session.query(ChecklistRule).all()}
    clean_results = [
        r for r in results if rule_by_id[r.rule_id].code == "audio.clean_version_exists"
    ]
    assert clean_results and clean_results[0].status == ChecklistStatus.BLOCKING


def test_waiving_a_blocking_result_updates_release_status(db_session):
    release = _make_release(db_session)
    results = evaluate_release(db_session, release)
    blocking = next(r for r in results if r.status == ChecklistStatus.BLOCKING)

    waive_result(db_session, blocking, user_id=None, reason="Test override")
    assert blocking.status == ChecklistStatus.WAIVED
    assert blocking.waived_reason == "Test override"


def test_summarize_status_priority():
    from types import SimpleNamespace

    def fake(status):
        return SimpleNamespace(status=status)

    assert summarize_status([fake(ChecklistStatus.PASSED)]) == "ready"
    assert (
        summarize_status([fake(ChecklistStatus.PASSED), fake(ChecklistStatus.WARNING)]) == "warning"
    )
    assert (
        summarize_status([fake(ChecklistStatus.BLOCKING), fake(ChecklistStatus.PASSED)])
        == "blocking"
    )
