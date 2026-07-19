"""CSV import templates for manual analytics entry (spec section 16)."""

from __future__ import annotations

import csv
import io

from produceros.models.enums import AnalyticsMetricType

CSV_TEMPLATE_HEADER = ["metric_type", "value", "channel", "content_reference"]

VALID_METRIC_TYPES = [m.value for m in AnalyticsMetricType]


def csv_template_text() -> str:
    """A ready-to-fill CSV template, with the two most common metric rows
    pre-populated as examples (values are placeholders, not real data)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_TEMPLATE_HEADER)
    writer.writerow(["streams", "0", "Spotify", ""])
    writer.writerow(["video_views", "0", "TikTok", "Reel 1"])
    return buf.getvalue()
