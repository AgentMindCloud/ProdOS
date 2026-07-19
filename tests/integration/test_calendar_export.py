from datetime import date, timedelta

from produceros.models.enums import DeadlineType
from produceros.services.calendar import create_deadline, export_ics, list_deadlines


def test_ics_export_contains_one_vevent_per_deadline(db_session):
    create_deadline(db_session, title="Mix delivery", deadline_type=DeadlineType.MIX_DELIVERY, due_date=date.today() + timedelta(days=5))
    create_deadline(db_session, title="Master approval", deadline_type=DeadlineType.MASTER_APPROVAL, due_date=date.today() + timedelta(days=10))

    deadlines = list_deadlines(db_session)
    ics = export_ics(deadlines)

    assert ics.count("BEGIN:VEVENT") == 2
    assert ics.count("END:VEVENT") == 2
    assert "SUMMARY:Mix delivery" in ics
    assert "SUMMARY:Master approval" in ics
    assert ics.startswith("BEGIN:VCALENDAR")
    assert ics.strip().endswith("END:VCALENDAR")


def test_ics_escapes_special_characters(db_session):
    create_deadline(db_session, title="Release; final, take", deadline_type=DeadlineType.RELEASE, due_date=date.today(), notes="Line one\nLine two")
    ics = export_ics(list_deadlines(db_session))
    assert "Release\\; final\\, take" in ics
    assert "Line one\\nLine two" in ics


def test_completed_deadlines_excluded_from_upcoming(db_session):
    from produceros.services.calendar import complete_deadline

    d = create_deadline(db_session, title="Done already", deadline_type=DeadlineType.RECORDING, due_date=date.today() + timedelta(days=2))
    complete_deadline(db_session, d)
    upcoming = list_deadlines(db_session, include_done=False)
    assert d not in upcoming
