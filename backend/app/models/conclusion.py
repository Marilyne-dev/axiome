"""Conclusions de travail par cycle (saisies par l'auditeur, éditables)."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CycleConclusion(Base):
    __tablename__ = "cycle_conclusions"
    __table_args__ = (UniqueConstraint("mission_id", "cycle_code", name="uq_conclusion_cycle"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    cycle_code: Mapped[str] = mapped_column(String(20))
    conclusion: Mapped[str] = mapped_column(Text, default="")
    anomalie: Mapped[bool] = mapped_column(Boolean, default=False)
    statut: Mapped[str] = mapped_column(String(20), default="en_cours")  # en_cours | finalise

    mission = relationship("Mission")
