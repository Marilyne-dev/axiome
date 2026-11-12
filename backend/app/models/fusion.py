"""Modèles du commissariat à la fusion : dossier d'échange et évaluations."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FusionDossier(Base, TimestampMixin):
    """Paramètres de l'opération de fusion (une par mission)."""

    __tablename__ = "fusion_dossier"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"),
                                            nullable=False, unique=True, index=True)
    nom_absorbante: Mapped[str] = mapped_column(String(160), default="Société absorbante")
    nom_absorbee: Mapped[str] = mapped_column(String(160), default="Société absorbée")
    actions_absorbante: Mapped[int] = mapped_column(Integer, default=0)
    actions_absorbee: Mapped[int] = mapped_column(Integer, default=0)
    valeur_nominale: Mapped[float] = mapped_column(Float, default=0.0)   # VN action absorbante
    parite_num: Mapped[int] = mapped_column(Integer, default=1)          # actions absorbante…
    parite_den: Mapped[int] = mapped_column(Integer, default=1)          # …pour actions absorbée


class FusionEvaluation(Base, TimestampMixin):
    """Valeur d'une société par une méthode d'évaluation (societe: A=absorbante, B=absorbée)."""

    __tablename__ = "fusion_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"),
                                            nullable=False, index=True)
    societe: Mapped[str] = mapped_column(String(1), nullable=False)   # "A" ou "B"
    methode: Mapped[str] = mapped_column(String(80), nullable=False)  # ANC, ANR, rendement, DCF…
    valeur: Mapped[float] = mapped_column(Float, default=0.0)
