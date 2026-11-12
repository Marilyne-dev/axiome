"""Base déclarative et mixins réutilisables."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Horodatage création/modification, géré côté serveur."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )


class SoftDeleteMixin:
    """Archivage logique (jamais de suppression physique des dossiers d'audit)."""

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
