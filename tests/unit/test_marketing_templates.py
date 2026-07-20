from produceros.marketing.context import PLACEHOLDER, build_project_context
from produceros.marketing.templates import TEMPLATES, render
from produceros.models.enums import MarketingDraftType
from produceros.services import catalog as catalog_service

FORBIDDEN_SUBSTRINGS = [
    "million streams",
    "grammy",
    "award-winning",
    "as seen on",
    "#1 on",
    "chart-topping",
]


def test_every_draft_type_has_a_template():
    for draft_type in MarketingDraftType:
        assert draft_type in TEMPLATES


def test_missing_data_renders_as_placeholder_not_invented(db_session):
    project = catalog_service.create_project(db_session, working_title="Untitled Track")
    context = build_project_context(db_session, project)
    assert context["genre"] == PLACEHOLDER
    assert context["release_date"] == PLACEHOLDER

    for draft_type in MarketingDraftType:
        title, body = render(draft_type, context)
        assert isinstance(title, str) and isinstance(body, str)


def test_templates_never_contain_fabricated_claims(db_session):
    project = catalog_service.create_project(db_session, working_title="Untitled Track")
    context = build_project_context(db_session, project)
    for draft_type in MarketingDraftType:
        _, body = render(draft_type, context)
        lowered = body.lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert (
                forbidden not in lowered
            ), f"{draft_type} draft contains fabricated claim: {forbidden!r}"


def test_confirmed_data_is_reflected_in_draft(db_session):
    project = catalog_service.create_project(
        db_session, working_title="Real Title", genre="Techno", bpm=128
    )
    context = build_project_context(db_session, project)
    title, body = render(MarketingDraftType.RELEASE_ANNOUNCEMENT, context)
    assert "Real Title" in title
    assert "Techno" in body
