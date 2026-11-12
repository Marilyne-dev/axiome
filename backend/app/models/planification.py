"""Module 4 — Planification de mission : plan, jalons, équipe, budget/honoraires."""
from __future__ import annotations

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PlanMission(Base, TimestampMixin):
    """Plan de mission (1-1 avec la mission)."""

    __tablename__ = "plans_mission"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), unique=True, nullable=False)
    date_debut: Mapped["object | None"] = mapped_column(Date, nullable=True)
    date_fin: Mapped["object | None"] = mapped_column(Date, nullable=True)
    approche: Mapped[str] = mapped_column(String(200), default="")   # substantive/contrôles…
    honoraires: Mapped[float] = mapped_column(Float, default=0.0)
    devise: Mapped[str] = mapped_column(String(3), default="EUR")

    jalons: Mapped[list["Jalon"]] = relationship(back_populates="plan", lazy="selectin")
    equipe: Mapped[list["AffectationEquipe"]] = relationship(back_populates="plan", lazy="selectin")
    budget: Mapped[list["LigneBudget"]] = relationship(back_populates="plan", lazy="selectin")


class Jalon(Base, TimestampMixin):
    """Jalon/étape planifiée (Gantt)."""

    __tablename__ = "jalons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans_mission.id", ondelete="CASCADE"), nullable=False)
    libelle: Mapped[str] = mapped_column(String(150), nullable=False)
    echeance: Mapped["object | None"] = mapped_column(Date, nullable=True)
    statut: Mapped[str] = mapped_column(String(20), default="a_faire")

    plan: Mapped[PlanMission] = relationship(back_populates="jalons")


class AffectationEquipe(Base, TimestampMixin):
    """Affectation d'un collaborateur à la mission, avec temps estimé."""

    __tablename__ = "affectations_equipe"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans_mission.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_mission: Mapped[str] = mapped_column(String(60), default="collaborateur")
    heures_estimees: Mapped[float] = mapped_column(Float, default=0.0)

    plan: Mapped[PlanMission] = relationship(back_populates="equipe")


class LigneBudget(Base, TimestampMixin):
    """Ligne de budget prévisionnel de la mission."""

    __tablename__ = "lignes_budget"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans_mission.id", ondelete="CASCADE"), nullable=False)
    poste: Mapped[str] = mapped_column(String(120), nullable=False)
    montant: Mapped[float] = mapped_column(Float, default=0.0)
    devise: Mapped[str] = mapped_column(String(3), default="EUR")

    plan: Mapped[PlanMission] = relationship(back_populates="budget")
