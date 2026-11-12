"""Feuille de travail éditable — cadrage TVA collectée (base × taux vs #4457)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LigneTVA(Base, TimestampMixin):
    __tablename__ = "analyse_tva"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    rubrique: Mapped[str] = mapped_column(String(80), default="")
    taux: Mapped[float] = mapped_column(Float, default=0.20)          # ex. 0.20
    base_ht: Mapped[float] = mapped_column(Float, default=0.0)        # base HT des ventes (à saisir)
    tva_comptabilisee: Mapped[float] = mapped_column(Float, default=0.0)  # #4457 collectée
    commentaire: Mapped[str] = mapped_column(Text, default="")

    mission = relationship("Mission")

    @property
    def tva_theorique(self) -> float:
        return round(self.base_ht * self.taux, 2)

    @property
    def ecart(self) -> float:
        return round(self.tva_theorique - self.tva_comptabilisee, 2)
