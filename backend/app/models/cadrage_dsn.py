"""Feuille de travail éditable — cadrage de la paie (FEC #64x vs DSN)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LigneCadrageDSN(Base, TimestampMixin):
    __tablename__ = "cadrage_dsn"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), index=True)
    compte: Mapped[str] = mapped_column(String(30), default="")
    libelle: Mapped[str] = mapped_column(String(200), default="")
    montant_fec: Mapped[float] = mapped_column(Float, default=0.0)   # comptabilisé (balance #64x)
    montant_dsn: Mapped[float] = mapped_column(Float, default=0.0)   # déclaré en DSN (à saisir)
    commentaire: Mapped[str] = mapped_column(Text, default="")

    mission = relationship("Mission")

    @property
    def ecart(self) -> float:
        return round(self.montant_fec - self.montant_dsn, 2)
