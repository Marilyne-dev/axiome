"""Module 9 — Programme d'audit : programmes par cycle et procédures."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ProgrammeAudit(Base, TimestampMixin):
    """Programme de travail d'un cycle (1-1)."""

    __tablename__ = "programmes_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id", ondelete="CASCADE"), unique=True, nullable=False)
    intitule: Mapped[str] = mapped_column(String(200), default="")
    statut: Mapped[str] = mapped_column(String(20), default="brouillon")  # brouillon|valide

    procedures: Mapped[list["ProcedureAudit"]] = relationship(back_populates="programme", lazy="selectin")


class ProcedureAudit(Base, TimestampMixin):
    """Procédure/diligence d'un programme, avec assertion visée."""

    __tablename__ = "procedures_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programme_id: Mapped[int] = mapped_column(ForeignKey("programmes_audit.id", ondelete="CASCADE"), nullable=False)
    reference: Mapped[str] = mapped_column(String(30), default="")
    libelle: Mapped[str] = mapped_column(Text, nullable=False)
    assertion: Mapped[str] = mapped_column(String(40), default="")   # existence, exhaustivite…
    fait: Mapped[bool] = mapped_column(Boolean, default=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    programme: Mapped[ProgrammeAudit] = relationship(back_populates="procedures")
