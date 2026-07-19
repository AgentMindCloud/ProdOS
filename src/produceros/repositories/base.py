"""Generic data-access layer shared by all services.

Keeping simple CRUD here means each service (produceros.services.*) only
has to implement the business rules specific to its domain -- rights-share
validation, checklist evaluation, pairing-code expiry, etc. -- rather than
re-writing session boilerplate.
"""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from produceros.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def get_or_404(self, entity_id: uuid.UUID) -> ModelT:
        instance = self.get(entity_id)
        if instance is None:
            raise LookupError(f"{self.model.__name__} {entity_id} not found")
        return instance

    def list_all(self, *, limit: int | None = None, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()

    def count(self) -> int:
        return len(self.list_all())
