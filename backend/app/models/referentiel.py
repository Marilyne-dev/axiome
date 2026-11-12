"""Référentiels comptables/fiscaux et règles fiscales paramétrables.

Règle d'architecture : le référentiel est une DIMENSION de la mission.
Aucune règle fiscale n'est codée en dur — tout vit dans RegleFiscale,
filtrable par (referentiel, pays). Ajouter un pays = insérer des lignes,
jamais modifier le code.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Referentiel(Base, TimestampMixin):
    """Référentiel comptable/fiscal actif (PCG_FR, IFRS, SYSCOHADA_OHADA, …)."""

    __tablename__ = "referentiels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    zone: Mapped[str] = mapped_column(String(80), default="")          # France, International, OHADA…
    norme_rapport: Mapped[str] = mapped_column(String(30), default="NEP")  # NEP | ISA
    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RegleFiscale(Base, TimestampMixin):
    """Règle fiscale paramétrable (taux TVA, IS…) rattachée à un référentiel + pays."""

    __tablename__ = "regles_fiscales"
    __table_args__ = (UniqueConstraint("referentiel_code", "pays", "code", name="uq_regle_ref_pays_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referentiel_code: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    pays: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)   # ex. TVA_NORMALE, IS_STD
    libelle: Mapped[str] = mapped_column(String(150), default="")
    taux: Mapped[float] = mapped_column(Float, default=0.0)         # ex. 0.20 pour 20 %
