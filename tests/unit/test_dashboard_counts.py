"""List limits must never silently cap the dashboard's summary numbers."""

from datetime import date

from produceros.models.calendar import Deadline
from produceros.models.catalog import Project
from produceros.models.enums import DeadlineType, ProjectState
from produceros.services.dashboard import build_summary


def test_summary_counts_are_not_limited_to_visible_rows(db_session):
    for i in range(12):
        db_session.add(
            Project(
                internal_code=f"COUNT-{i}", working_title=f"Project {i}", state=ProjectState.IDEA
            )
        )
        db_session.add(
            Deadline(
                title=f"Deadline {i}",
                due_date=date.today(),
                deadline_type=DeadlineType.MASTER_APPROVAL,
            )
        )
    db_session.flush()
    summary = build_summary(db_session)
    assert summary.active_project_count == 12
    assert summary.unconfirmed_rights_count == 12
    assert summary.deadline_count == 12
    assert len(summary.active_projects) == 8
    assert len(summary.upcoming_deadlines) == 10
