from produceros.models.enums import RightsShareType
from produceros.services import catalog as catalog_service
from produceros.services import rights as rights_service


def _make_project(db_session):
    return catalog_service.create_project(db_session, working_title="Test Track")


def test_rights_shares_totaling_100_have_no_warning(db_session):
    project = _make_project(db_session)
    rights_service.add_rights_share(db_session, project.id, holder_name="A", share_type=RightsShareType.MASTER, percentage=60, confirmed=True)
    rights_service.add_rights_share(db_session, project.id, holder_name="B", share_type=RightsShareType.MASTER, percentage=40, confirmed=True)

    validations = rights_service.validate_rights_shares(db_session, project.id)
    assert len(validations) == 1
    assert validations[0].is_exactly_100
    assert validations[0].warning is None


def test_rights_shares_not_totaling_100_warn(db_session):
    project = _make_project(db_session)
    rights_service.add_rights_share(db_session, project.id, holder_name="A", share_type=RightsShareType.MASTER, percentage=60, confirmed=True)
    rights_service.add_rights_share(db_session, project.id, holder_name="B", share_type=RightsShareType.MASTER, percentage=30, confirmed=True)

    validations = rights_service.validate_rights_shares(db_session, project.id)
    assert not validations[0].is_exactly_100
    assert validations[0].warning is not None
    assert "90" in validations[0].warning


def test_rights_shares_100_but_unconfirmed_warn(db_session):
    project = _make_project(db_session)
    rights_service.add_rights_share(db_session, project.id, holder_name="A", share_type=RightsShareType.MASTER, percentage=100, confirmed=False)

    validations = rights_service.validate_rights_shares(db_session, project.id)
    assert validations[0].is_exactly_100
    assert not validations[0].all_confirmed
    assert validations[0].warning is not None


def test_no_shares_returns_no_validation_rows(db_session):
    project = _make_project(db_session)
    assert rights_service.validate_rights_shares(db_session, project.id) == []


def test_percentage_never_changes_except_via_explicit_update(db_session):
    project = _make_project(db_session)
    share = rights_service.add_rights_share(db_session, project.id, holder_name="A", share_type=RightsShareType.MASTER, percentage=50, confirmed=True)
    assert share.percentage == 50

    # Merely re-validating must never mutate the stored percentage.
    rights_service.validate_rights_shares(db_session, project.id)
    db_session.refresh(share)
    assert share.percentage == 50

    rights_service.update_rights_share_percentage(db_session, share, 55, user_id=None)
    assert share.percentage == 55
