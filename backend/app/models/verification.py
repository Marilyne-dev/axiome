"""Modèles des vérifications spécifiques du commissaire aux comptes (art. L.823-10).

- VerifConcordance : rapprochement d'un montant déclaré au rapport de gestion avec
  le montant issu des comptes ;
- VerifPoint : point de contrôle qualitatif (fait / observation).
"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VerifConcordance(Base, TimestampMixin):
    __tablename__ = "verif_concordance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    libelle: Mapped[str] = mapped_column(String(160), nullable=False)
    montant_comptes: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    montant_rapport: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation: Mapped[str] = mapped_column(String(400), default="")


class VerifPoint(Base, TimestampMixin):
    __tablename__ = "verif_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    libelle: Mapped[str] = mapped_column(String(200), nullable=False)
    fait: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observation: Mapped[str] = mapped_column(String(400), default="")
