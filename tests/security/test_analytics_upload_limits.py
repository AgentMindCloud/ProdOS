"""Bound CSV resource use before multipart parsing and database insertion."""

import pytest
from sqlalchemy import func, select

from produceros.analytics.importer import MAX_IMPORT_ROWS, CSVImportError, parse_analytics_csv
from produceros.db.session import get_sessionmaker
from produceros.models.analytics import AnalyticsImport, AnalyticsMetric
from produceros.web.routes.analytics import MAX_CSV_BYTES, MAX_IMPORT_REQUEST_BYTES
from tests.conftest import complete_setup, get_form_csrf


def import_form(client):
    return {
        "csrf_token": get_form_csrf(client, "/analytics"),
        "period_start": "2026-09-01",
        "period_end": "2026-09-09",
    }


def assert_no_imports():
    with get_sessionmaker()() as session:
        assert session.scalar(select(func.count()).select_from(AnalyticsImport)) == 0
        assert session.scalar(select(func.count()).select_from(AnalyticsMetric)) == 0


def test_csv_import_with_excel_bom_succeeds(client):
    complete_setup(client)
    response = client.post(
        "/analytics/import",
        data=import_form(client),
        files={
            "csv_file": ("metrics.csv", b"\xef\xbb\xbfmetric_type,value\nstreams,100\n", "text/csv")
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with get_sessionmaker()() as session:
        assert session.scalar(select(AnalyticsMetric.value)) == 100


def test_csv_file_over_size_limit_is_rejected_without_import(client):
    complete_setup(client)
    response = client.post(
        "/analytics/import",
        data=import_form(client),
        files={"csv_file": ("metrics.csv", b"x" * (MAX_CSV_BYTES + 1), "text/csv")},
    )
    assert response.status_code == 413
    assert_no_imports()


def test_chunked_request_without_content_length_is_still_bounded(client):
    complete_setup(client)
    response = client.post(
        "/analytics/import",
        content=iter([b"x" * (MAX_IMPORT_REQUEST_BYTES + 1)]),
        headers={"Content-Type": "multipart/form-data; boundary=test"},
    )
    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert_no_imports()


def test_csv_over_row_limit_is_rejected_without_partial_import(client):
    complete_setup(client)
    content = "metric_type,value\n" + "streams,1\n" * (MAX_IMPORT_ROWS + 1)
    response = client.post(
        "/analytics/import",
        data=import_form(client),
        files={"csv_file": ("metrics.csv", content, "text/csv")},
    )
    assert response.status_code == 400
    assert_no_imports()


def test_oversized_csv_field_is_a_validation_error(client):
    complete_setup(client)
    content = "metric_type,value\nstreams," + "1" * 140_000
    response = client.post(
        "/analytics/import",
        data=import_form(client),
        files={"csv_file": ("metrics.csv", content, "text/csv")},
    )
    assert response.status_code == 400
    assert_no_imports()


def test_reversed_import_period_is_rejected(client):
    complete_setup(client)
    form = import_form(client)
    form["period_end"] = "2026-08-31"
    response = client.post(
        "/analytics/import",
        data=form,
        files={"csv_file": ("metrics.csv", "metric_type,value\nstreams,10\n", "text/csv")},
    )
    assert response.status_code == 400
    assert_no_imports()


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_csv_numbers_are_rejected(number):
    result = parse_analytics_csv(f"metric_type,value\nstreams,{number}\n")
    assert not result.rows
    assert any("finite" in warning for warning in result.warnings)


def test_row_limit_also_bounds_invalid_row_warnings():
    with pytest.raises(CSVImportError, match="10,000"):
        parse_analytics_csv("metric_type,value\n" + "unknown,1\n" * (MAX_IMPORT_ROWS + 1))
