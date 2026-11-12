"""Clients audités et groupes de consolidation."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Groupe(Base, TimestampMixin):
    """Groupe (périmètre de consolidation)."""

    __tablename__ = "groupes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(180), nullable=False)


class Client(Base, TimestampMixin, SoftDeleteMixin):
    """Entité auditée."""

    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False)
    groupe_id: Mapped[int | None] = mapped_column(ForeignKey("groupes.id", ondelete="SET NULL"), nullable=True)

    raison_sociale: Mapped[str] = mapped_column(String(200), nullable=False)
    identifiant_legal: Mapped[str] = mapped_column(String(60), default="")  # SIREN, RCCM, etc.
    pays: Mapped[str] = mapped_column(String(80), default="France")
    secteur: Mapped[str] = mapped_column(String(120), default="")

    missions: Mapped[list["object"]] = relationship(
        "Mission", back_populates="client", lazy="selectin"
    )
