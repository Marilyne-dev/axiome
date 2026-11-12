"""Cabinet d'audit et ses bureaux/agences (multi-pays)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Cabinet(Base, TimestampMixin, SoftDeleteMixin):
    """Cabinet titulaire de la licence AXIOME."""

    __tablename__ = "cabinets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(180), nullable=False)
    pays: Mapped[str] = mapped_column(String(80), default="France")
    devise_defaut: Mapped[str] = mapped_column(String(3), default="EUR")  # code ISO 4217
    referentiel_defaut: Mapped[str] = mapped_column(String(30), default="PCG_FR")
    quota_collaborateurs: Mapped[int] = mapped_column(Integer, default=0)  # 0 = illimité
    quota_missions: Mapped[int] = mapped_column(Integer, default=0)         # 0 = illimité

    bureaux: Mapped[list["Bureau"]] = relationship(back_populates="cabinet", lazy="selectin")


class Bureau(Base, TimestampMixin):
    """Bureau/agence d'un cabinet, potentiellement dans un autre pays/devise."""

    __tablename__ = "bureaux"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id", ondelete="CASCADE"), nullable=False)
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    ville: Mapped[str] = mapped_column(String(120), default="")
    pays: Mapped[str] = mapped_column(String(80), default="France")

    cabinet: Mapped[Cabinet] = relationship(back_populates="bureaux")
