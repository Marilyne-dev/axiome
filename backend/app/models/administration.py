"""Module 1 — Administration du cabinet : modèles de documents réutilisables."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ModeleDocument(Base, TimestampMixin):
    """Modèle de document paramétrable (lettre de mission, rapport, etc.)."""

    __tablename__ = "modeles_document"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)     # LETTRE_MISSION, RAPPORT_GENERAL…
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    referentiel: Mapped[str] = mapped_column(String(30), default="")  # vide = tous référentiels
    langue: Mapped[str] = mapped_column(String(5), default="fr")
    corps: Mapped[str] = mapped_column(Text, default="")             # gabarit (placeholders {client}…)
