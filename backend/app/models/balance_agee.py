"""Feuille de travail éditable — balance âgée clients / fournisseurs."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BalanceAgee(Base, TimestampMixin):
    __tablename__ = "balances_agees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    cycle: Mapped[str] = mapped_column(String(20), index=True)  # "CLIENTS" | "FOURNISSEURS"
    compte: Mapped[str] = mapped_column(String(30), default="")
    libelle: Mapped[str] = mapped_column(String(200), default="")
    solde_comptable: Mapped[float] = mapped_column(Float, default=0.0)
    non_echu: Mapped[float] = mapped_column(Float, default=0.0)
    echu_30: Mapped[float] = mapped_column(Float, default=0.0)
    echu_60: Mapped[float] = mapped_column(Float, default=0.0)
    echu_90: Mapped[float] = mapped_column(Float, default=0.0)
    echu_plus: Mapped[float] = mapped_column(Float, default=0.0)
    commentaire: Mapped[str] = mapped_column(Text, default="")

    mission = relationship("Mission")

    @property
    def total_ventile(self) -> float:
        return round(self.non_echu + self.echu_30 + self.echu_60 + self.echu_90 + self.echu_plus, 2)

    @property
    def ecart(self) -> float:
        return round(self.solde_comptable - self.total_ventile, 2)
