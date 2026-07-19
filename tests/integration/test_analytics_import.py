from datetime import date, timedelta

from produceros.analytics.importer import parse_analytics_csv
from produceros.analytics.summaries import channel_summary, release_summary
from produceros.models.enums import AnalyticsSourceType
from produceros.services import catalog as catalog_service
from produceros.services.analytics import get_or_create_source, record_import


def test_csv_import_reflected_in_release_summary(db_session):
    project = catalog_service.create_project(db_session, working_title="Analytics Track")
    source = get_or_create_source(db_session, "Spotify Export", AnalyticsSourceType.STREAMING)
    parsed = parse_analytics_csv("metric_type,value,channel\nstreams,1000,Spotify\nsaves,50,Spotify\n")

    record_import(
        db_session, source=source, parsed=parsed,
        reporting_period_start=date.today() - timedelta(days=7), reporting_period_end=date.today(),
        project_id=project.id,
    )

    summary = release_summary(db_session, project.id)
    values = {m.metric_type: m.total for m in summary}
    assert values["streams"] == 1000
    assert values["saves"] == 50

    channels = channel_summary(db_session, project_id=project.id)
    assert channels["Spotify"] == 1050


def test_import_warnings_are_preserved(db_session):
    project = catalog_service.create_project(db_session, working_title="Analytics Track")
    source = get_or_create_source(db_session, "Messy Export", AnalyticsSourceType.OTHER)
    parsed = parse_analytics_csv("metric_type,value\nstreams,100\nnot_a_metric,5\n")
    assert parsed.warnings  # unknown metric type produced a warning

    import_row = record_import(
        db_session, source=source, parsed=parsed,
        reporting_period_start=date.today() - timedelta(days=1), reporting_period_end=date.today(),
        project_id=project.id,
    )
    assert import_row.warnings == parsed.warnings
    assert import_row.row_count == 1
