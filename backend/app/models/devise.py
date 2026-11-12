"""Devises ISO 4217 et taux de change (aucune devise codée en dur ailleurs)."""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Devise(Base):
    """Devise du référentiel ISO 4217. Jeu complet chargé au seed."""

    __tablename__ = "devises"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, index=True, nullable=False)  # EUR, USD, XOF…
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    symbole: Mapped[str] = mapped_column(String(8), default="")
    decimales: Mapped[int] = mapped_column(Integer, default=2)
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TauxDeChange(Base, TimestampMixin):
    """Taux de conversion source→cible à une date (paramétrable ou via API)."""

    __tablename__ = "taux_de_change"
    __table_args__ = (UniqueConstraint("source", "cible", "date_taux", name="uq_taux_src_cible_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(ForeignKey("devises.code"), nullable=False)
    cible: Mapped[str] = mapped_column(ForeignKey("devises.code"), nullable=False)
    taux: Mapped[float] = mapped_column(Float, nullable=False)
    date_taux: Mapped["object"] = mapped_column(DateTime(timezone=True), server_default=func.now())
