"""Missions d'audit et cycles.

Chaque mission porte sa DIMENSION (referentiel, pays, devise). Rien n'est figé :
une mission peut être libellée dans n'importe quelle devise (EUR par défaut).
"""
from __future__ import annotations

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Mission(Base, TimestampMixin, SoftDeleteMixin):
    """Mission (commissariat aux comptes / audit contractuel)."""

    __tablename__ = "missions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    intitule: Mapped[str] = mapped_column(String(200), nullable=False)
    exercice: Mapped[str] = mapped_column(String(9), default="")  # ex. 2025

    # Typologie CAC : type de mission (certification, durabilité, alerte, capital…)
    type_mission: Mapped[str] = mapped_column(String(30), default="CERT_ANNUELS", index=True)

    # Dimension métier — jamais codée en dur
    referentiel: Mapped[str] = mapped_column(String(30), default="PCG_FR", index=True)
    pays: Mapped[str] = mapped_column(String(80), default="France")
    devise: Mapped[str] = mapped_column(String(3), default="EUR")  # ISO 4217

    statut: Mapped[str] = mapped_column(String(30), default="acceptation")  # acceptation→planification→…
    date_cloture: Mapped["object | None"] = mapped_column(Date, nullable=True)

    client: Mapped["object"] = relationship("Client", back_populates="missions")
    cycles: Mapped[list["Cycle"]] = relationship(back_populates="mission", lazy="selectin")


class Cycle(Base, TimestampMixin):
    """Cycle d'audit d'une mission (Trésorerie, Achats, Ventes, Emprunts…)."""

    __tablename__ = "cycles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)   # TRESORERIE, EMPRUNTS…
    libelle: Mapped[str] = mapped_column(String(120), nullable=False)
    statut: Mapped[str] = mapped_column(String(30), default="a_faire")

    mission: Mapped[Mission] = relationship(back_populates="cycles")


class MissionDiligence(Base, TimestampMixin):
    """État d'une diligence (checklist) propre au type de mission."""

    __tablename__ = "mission_diligences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(60), nullable=False)  # index de la diligence (0,1,2…)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    fait: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
