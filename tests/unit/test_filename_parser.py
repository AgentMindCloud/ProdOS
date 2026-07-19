from datetime import date

from produceros.scanners.filename_parser import parse_filename


def test_artist_track_stage_version_date():
    result = parse_filename("Artist_TrackName_MIX_v03_2026-07-19.wav")
    assert result.artist == "Artist"
    assert result.track == "TrackName"
    assert result.mix_or_master == "mix"
    assert result.version_number == 3
    assert result.parsed_date == date(2026, 7, 19)


def test_dashed_artist_track_master_version():
    result = parse_filename("Artist - Track Name - Master v2.wav")
    assert result.artist == "Artist"
    assert result.track == "Track Name"
    assert result.mix_or_master == "master"
    assert result.version_number == 2


def test_instrumental_bpm_key():
    result = parse_filename("TrackName_Instrumental_120BPM_Am.wav")
    assert result.track == "TrackName"
    assert result.mix_or_master == "instrumental"
    assert result.bpm == 120.0
    assert result.musical_key == "Am"


def test_fl_project_version():
    result = parse_filename("TrackName_FL_v12.flp")
    assert result.track == "TrackName"
    assert result.version_number == 12
    assert result.asset_hint == "fl_project"


def test_unparseable_filename_does_not_raise():
    result = parse_filename("random_export_final_FINAL2.wav")
    assert result.original_filename == "random_export_final_FINAL2.wav"


def test_original_filename_never_mutated():
    original = "Artist_TrackName_MIX_v03_2026-07-19.wav"
    result = parse_filename(original)
    assert result.original_filename == original
