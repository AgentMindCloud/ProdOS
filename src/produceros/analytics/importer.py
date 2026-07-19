"""Manual CSV import parsing (spec section 16). No platform API calls --
the producer exports a CSV from wherever they track numbers and imports it
here; malformed rows become warnings, never silent data loss or guesses."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from produceros.analytics.csv_templates import VALID_METRIC_TYPES


@dataclass
class ImportedRow:
    metric_type: str
    value: float
    channel: str | None
    content_reference: str | None


@dataclass
class ParseResult:
    rows: list[ImportedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_analytics_csv(content: str) -> ParseResult:
    result = ParseResult()
    reader = csv.DictReader(io.StringIO(content))

    if reader.fieldnames is None:
        result.warnings.append("CSV file is empty or has no header row.")
        return result

    required = {"metric_type", "value"}
    missing_columns = required - {c.strip().lower() for c in reader.fieldnames}
    if missing_columns:
        result.warnings.append(f"Missing required column(s): {', '.join(sorted(missing_columns))}.")
        return result

    normalized_fieldnames = {name: name.strip().lower() for name in reader.fieldnames}

    for line_number, raw_row in enumerate(reader, start=2):
        row = {normalized_fieldnames[k]: v for k, v in raw_row.items() if k in normalized_fieldnames}
        metric_type = (row.get("metric_type") or "").strip().lower()
        raw_value = (row.get("value") or "").strip()

        if not metric_type:
            result.warnings.append(f"Row {line_number}: missing metric_type; skipped.")
            continue
        if metric_type not in VALID_METRIC_TYPES:
            result.warnings.append(f"Row {line_number}: unknown metric_type '{metric_type}'; skipped.")
            continue
        try:
            value = float(raw_value)
        except ValueError:
            result.warnings.append(f"Row {line_number}: value '{raw_value}' is not numeric; skipped.")
            continue
        if value < 0:
            result.warnings.append(f"Row {line_number}: negative value for '{metric_type}'; kept, please verify.")

        result.rows.append(
            ImportedRow(
                metric_type=metric_type,
                value=value,
                channel=(row.get("channel") or "").strip() or None,
                content_reference=(row.get("content_reference") or "").strip() or None,
            )
        )

    if not result.rows:
        result.warnings.append("No valid data rows found in the CSV.")

    return result
