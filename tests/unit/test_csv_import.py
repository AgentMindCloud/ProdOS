from produceros.analytics.importer import parse_analytics_csv


def test_valid_csv_parses_all_rows():
    csv_text = "metric_type,value,channel,content_reference\nstreams,100,Spotify,\nvideo_views,50,TikTok,Reel 1\n"
    result = parse_analytics_csv(csv_text)
    assert len(result.rows) == 2
    assert not result.warnings
    assert result.rows[0].metric_type == "streams"
    assert result.rows[0].value == 100.0
    assert result.rows[1].content_reference == "Reel 1"


def test_missing_required_columns_produces_warning():
    result = parse_analytics_csv("foo,bar\n1,2\n")
    assert not result.rows
    assert any("missing" in w.lower() for w in result.warnings)


def test_unknown_metric_type_skipped_with_warning():
    csv_text = "metric_type,value\nnot_a_real_metric,10\nstreams,10\n"
    result = parse_analytics_csv(csv_text)
    assert len(result.rows) == 1
    assert any("unknown metric_type" in w for w in result.warnings)


def test_non_numeric_value_skipped_with_warning():
    csv_text = "metric_type,value\nstreams,not-a-number\n"
    result = parse_analytics_csv(csv_text)
    assert not result.rows
    assert any("not numeric" in w for w in result.warnings)


def test_negative_value_kept_but_warned():
    csv_text = "metric_type,value\nrevenue,-50\n"
    result = parse_analytics_csv(csv_text)
    assert len(result.rows) == 1
    assert any("negative value" in w for w in result.warnings)


def test_empty_csv_warns():
    result = parse_analytics_csv("")
    assert not result.rows
    assert result.warnings
