"""Artist / Project / Track catalog management, including the workflow
state machine and its audit trail (spec sections 7-8)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from produceros.models.catalog import Artist, Project, ProjectTag, Tag, Track
from produceros.models.enums import DEFAULT_PROJECT_STATES, ProjectState
from produceros.services.audit import log_event


class InvalidStateTransition(ValueError):
    pass


def next_internal_code(session: Session) -> str:
    count = session.scalar(select(func.count()).select_from(Project)) or 0
    return f"PRJ-{count + 1:04d}"


def create_project(
    session: Session,
    *,
    working_title: str,
    artist_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    **extra_fields,
) -> Project:
    project = Project(
        internal_code=next_internal_code(session),
        working_title=working_title.strip(),
        artist_id=artist_id,
        state=ProjectState.IDEA,
        **extra_fields,
    )
    session.add(project)
    session.flush()
    log_event(
        session,
        event_type="project.created",
        summary=f"Project '{project.working_title}' ({project.internal_code}) created.",
        user_id=user_id,
        entity_type="Project",
        entity_id=project.id,
    )
    return project


def update_project(
    session: Session, project: Project, *, user_id: uuid.UUID | None = None, **fields
) -> Project:
    changed = []
    for key, value in fields.items():
        if not hasattr(project, key):
            continue
        if getattr(project, key) != value:
            setattr(project, key, value)
            changed.append(key)
    if changed:
        session.flush()
        log_event(
            session,
            event_type="project.updated",
            summary=f"Project '{project.working_title}' updated fields: {', '.join(changed)}.",
            user_id=user_id,
            entity_type="Project",
            entity_id=project.id,
            metadata={"changed_fields": changed},
        )
    return project


def change_project_state(
    session: Session,
    project: Project,
    new_state: ProjectState,
    *,
    user_id: uuid.UUID | None = None,
    note: str | None = None,
) -> Project:
    if new_state.value not in DEFAULT_PROJECT_STATES:
        raise InvalidStateTransition(f"Unknown project state: {new_state}")
    old_state = project.state
    if old_state == new_state:
        return project
    project.state = new_state
    session.flush()
    log_event(
        session,
        event_type="project.state_changed",
        summary=f"Project '{project.working_title}' moved from {old_state} to {new_state}.",
        user_id=user_id,
        entity_type="Project",
        entity_id=project.id,
        metadata={"from": str(old_state), "to": str(new_state), "note": note},
    )
    return project


def get_or_create_tag(session: Session, name: str, category: str | None = None) -> Tag:
    normalized = name.strip()
    tag = session.scalar(select(Tag).where(func.lower(Tag.name) == normalized.lower()))
    if tag is None:
        tag = Tag(name=normalized, category=category)
        session.add(tag)
        session.flush()
    return tag


def set_project_tags(session: Session, project: Project, tag_names: list[str]) -> None:
    session.query(ProjectTag).filter(ProjectTag.project_id == project.id).delete()
    for name in tag_names:
        if not name.strip():
            continue
        tag = get_or_create_tag(session, name)
        session.add(ProjectTag(project_id=project.id, tag_id=tag.id))
    session.flush()


def list_projects(
    session: Session,
    *,
    artist_id: uuid.UUID | None = None,
    state: ProjectState | None = None,
    search: str | None = None,
) -> list[Project]:
    stmt = select(Project)
    if artist_id:
        stmt = stmt.where(Project.artist_id == artist_id)
    if state:
        stmt = stmt.where(Project.state == state)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            (Project.working_title.ilike(like))
            | (Project.final_title.ilike(like))
            | (Project.internal_code.ilike(like))
        )
    stmt = stmt.order_by(Project.updated_at.desc())
    return list(session.scalars(stmt))


def create_artist(
    session: Session, *, name: str, user_id: uuid.UUID | None = None, **fields
) -> Artist:
    artist = Artist(name=name.strip(), **fields)
    session.add(artist)
    session.flush()
    log_event(
        session,
        event_type="artist.created",
        summary=f"Artist '{artist.name}' created.",
        user_id=user_id,
        entity_type="Artist",
        entity_id=artist.id,
    )
    return artist


def create_track(session: Session, project: Project, *, title: str, **fields) -> Track:
    track = Track(project_id=project.id, title=title.strip(), **fields)
    session.add(track)
    session.flush()
    return track
