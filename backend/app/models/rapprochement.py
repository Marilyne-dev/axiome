"""Feuille de travail éditable — rapprochement bancaire (cycle Trésorerie)."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RapprochementBancaire(Base, TimestampMixin):
    __tablename__ = "rapprochements_bancaires"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    compte: Mapped[str] = mapped_column(String(30), default="")
    libelle: Mapped[str] = mapped_column(String(200), default="")
    solde_comptable: Mapped[float] = mapped_column(Float, default=0.0)
    solde_releve: Mapped[float] = mapped_column(Float, default=0.0)
    valide: Mapped[bool] = mapped_column(Boolean, default=False)
    commentaire: Mapped[str] = mapped_column(Text, default="")

    mission = relationship("Mission")

    @property
    def ecart(self) -> float:
        return round(self.solde_comptable - self.solde_releve, 2)
