"""Module 11 — Échantillonnage : éléments sélectionnés (Sample est dans audit.py)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SampleItem(Base, TimestampMixin):
    """Élément (pièce) sélectionné dans un échantillon."""

    __tablename__ = "sample_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    reference_piece: Mapped[str] = mapped_column(String(60), default="")
    montant: Mapped[float] = mapped_column(Float, default=0.0)
    devise: Mapped[str] = mapped_column(String(3), default="EUR")
    conclusion: Mapped[str] = mapped_column(String(20), default="a_tester")  # ok|anomalie|a_tester
