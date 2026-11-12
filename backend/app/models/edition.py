"""Journal des éditions de livrables (traçabilité ISQM).

Chaque génération de rapport/classeur est consignée avec l'auteur (dénormalisé,
donc immuable même si l'utilisateur est renommé ou supprimé), le type, le format
et l'horodatage.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RapportEdition(Base, TimestampMixin):
    __tablename__ = "rapport_editions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    type_edition: Mapped[str] = mapped_column(String(60), nullable=False)  # ex. dossier-complet, cycle:TRESORERIE
    format: Mapped[str] = mapped_column(String(10), default="")            # xlsx | docx | pdf
    par: Mapped[str] = mapped_column(String(150), default="")             # auteur dénormalisé (immuable)
