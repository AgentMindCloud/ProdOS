"""Builds the *only* data marketing templates are allowed to see: confirmed
fields already stored on the Project/Release/Artist. Nothing here ever
calls an external service or invents a value (spec section 13)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from produceros.models.catalog import Project
from produceros.models.release import Release

PLACEHOLDER = "[fill in]"


def _s(value, placeholder: str = PLACEHOLDER) -> str:
    if value in (None, "", []):
        return placeholder
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else placeholder
    return str(value)


def build_project_context(session: Session, project: Project, release: Release | None = None) -> dict:
    artist_name = project.artist.name if project.artist else None
    return {
        "artist_name": _s(artist_name),
        "working_title": _s(project.working_title),
        "title": _s(project.final_title or project.working_title),
        "featured_artists": _s(project.featured_artists),
        "genre": _s(project.genre),
        "subgenre": _s(project.subgenre),
        "mood": _s(project.mood),
        "bpm": _s(project.bpm),
        "musical_key": _s(project.musical_key),
        "language": _s(project.language),
        "instruments": _s(project.instruments),
        "vocal_style": _s(project.vocal_style),
        "similar_artists": _s(project.similar_artists),
        "release_date": _s(release.release_date if release else project.release_date),
        "distributor": _s(release.distributor if release else project.distributor),
        "isrc": _s(release.isrc if release else project.isrc),
        "upc": _s(release.upc if release else project.upc),
        "explicit_status": _s(
            (release.explicit_status.value if release else project.explicit_status.value)
        ),
        "release_type": _s(release.release_type.value.replace("_", " ") if release else (project.release_type.value.replace("_", " ") if project.release_type else None)),
        "description": _s(release.description if release else project.release_description),
        "internal_code": project.internal_code,
    }
