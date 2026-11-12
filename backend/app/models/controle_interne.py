"""Module 8 — Contrôle interne (référentiel COSO).

Évaluation par processus/cycle : tests de cheminement (walkthrough), contrôles
clés, faiblesses et recommandations. Rattaché au cycle de la mission.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Composantes COSO (référence, non figée dans le code métier).
COMPOSANTES_COSO = (
    "environnement_controle", "evaluation_risques", "activites_controle",
    "information_communication", "pilotage",
)


class ControleInterne(Base, TimestampMixin):
    """Point de contrôle interne évalué sur un cycle."""

    __tablename__ = "controles_interne"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False)
    composante_coso: Mapped[str] = mapped_column(String(40), default="activites_controle")
    intitule: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    walkthrough: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(String(20), default="a_tester")  # efficace|deficient|a_tester

    faiblesses: Mapped[list["Faiblesse"]] = relationship(back_populates="controle", lazy="selectin")


class Faiblesse(Base, TimestampMixin):
    """Faiblesse de contrôle interne + recommandation associée."""

    __tablename__ = "faiblesses_ci"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    controle_id: Mapped[int] = mapped_column(ForeignKey("controles_interne.id", ondelete="CASCADE"), nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    gravite: Mapped[str] = mapped_column(String(20), default="mineure")  # mineure|significative|majeure
    recommandation: Mapped[str] = mapped_column(Text, default="")

    controle: Mapped[ControleInterne] = relationship(back_populates="faiblesses")
