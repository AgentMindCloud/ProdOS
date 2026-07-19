from sqlalchemy import select

from produceros.models.enums import ProjectState
from produceros.models.system import AuditEvent
from produceros.services import catalog as catalog_service


def test_project_creation_and_state_change_are_audited(db_session):
    project = catalog_service.create_project(db_session, working_title="Audited Track")
    catalog_service.change_project_state(db_session, project, ProjectState.MIX, note="Ready for mixing")

    events = list(db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == project.id)))
    event_types = {e.event_type for e in events}
    assert "project.created" in event_types
    assert "project.state_changed" in event_types


def test_login_events_are_audited(client):
    from tests.conftest import complete_setup, get_form_csrf

    complete_setup(client)
    client.cookies.clear()
    csrf = get_form_csrf(client, "/login")
    client.post("/login", data={"csrf_token": csrf, "username": "producer", "password": "wrong"})

    from produceros.db.session import get_sessionmaker

    session = get_sessionmaker()()
    try:
        events = list(session.scalars(select(AuditEvent).where(AuditEvent.event_type == "auth.login_failed")))
        assert len(events) >= 1
    finally:
        session.close()


def test_audit_events_never_contain_password(db_session):
    from produceros.services.auth import create_first_admin

    create_first_admin(db_session, username="someone", password="super-secret-password-123", display_name="Someone")
    events = list(db_session.scalars(select(AuditEvent)))
    for event in events:
        assert "super-secret-password-123" not in event.summary
        assert "super-secret-password-123" not in str(event.event_metadata)
