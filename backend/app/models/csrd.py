"""Modèles du module CSRD : double matérialité et couverture des points ESRS."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CsrdMateriality(Base, TimestampMixin):
    """Évaluation de double matérialité d'un thème ESRS pour une mission."""

    __tablename__ = "csrd_materialite"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    esrs_code: Mapped[str] = mapped_column(String(10), nullable=False)     # E1, S1, G1…
    impact: Mapped[int] = mapped_column(Integer, default=0, nullable=False)     # 0..3 (matérialité d'impact)
    financier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0..3 (matérialité financière)
    retenu: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    justification: Mapped[str] = mapped_column(String(500), default="")


class CsrdPoint(Base, TimestampMixin):
    """Couverture d'un point de données ESRS pour une mission (thèmes retenus)."""

    __tablename__ = "csrd_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    esrs_code: Mapped[str] = mapped_column(String(10), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)   # E1-6, S1-16…
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    couvert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
