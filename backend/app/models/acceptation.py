"""Module 3 — Acceptation et maintien de la mission.

Diligences préalables : indépendance, KYC/LAB, conflits d'intérêts, continuité,
questionnaire d'acceptation, décision, lettre de mission. La décision reste
un acte humain (associé signataire) : l'outil aide, ne décide jamais seul.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Acceptation(Base, TimestampMixin):
    """Dossier d'acceptation/maintien rattaché à une mission (1-1)."""

    __tablename__ = "acceptations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id", ondelete="CASCADE"), unique=True, nullable=False)

    independance_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    conflit_interet: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    continuite_exploitation_ok: Mapped[bool] = mapped_column(Boolean, default=True)

    niveau_risque_global: Mapped[str] = mapped_column(String(20), default="standard")  # faible|standard|eleve
    # Réponses au questionnaire d'acceptation, stockées en JSON textuel (souple, versionnable).
    questionnaire: Mapped[str] = mapped_column(Text, default="{}")

    decision: Mapped[str] = mapped_column(String(20), default="en_cours")  # en_cours|acceptee|refusee
    decideur_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    motivation: Mapped[str] = mapped_column(Text, default="")

    lettre_mission: Mapped["LettreMission | None"] = relationship(
        back_populates="acceptation", uselist=False, lazy="selectin"
    )


class LettreMission(Base, TimestampMixin):
    """Lettre de mission générée puis acceptée (électroniquement)."""

    __tablename__ = "lettres_mission"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    acceptation_id: Mapped[int] = mapped_column(ForeignKey("acceptations.id", ondelete="CASCADE"), unique=True, nullable=False)
    reference: Mapped[str] = mapped_column(String(60), default="")
    corps: Mapped[str] = mapped_column(Text, default="")
    statut: Mapped[str] = mapped_column(String(20), default="brouillon")  # brouillon|envoyee|signee

    acceptation: Mapped[Acceptation] = relationship(back_populates="lettre_mission")
