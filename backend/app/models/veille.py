"""Module 26 — Veille réglementaire (entrées de référence + saisie manuelle).

Note d'honnêteté : ce module n'est PAS connecté à des flux officiels temps réel.
Il fournit une base de veille alimentable manuellement, amorcée par quelques entrées
de référence stables. Une alimentation automatique (ANC, CNCC, H2A, IAASB, OHADA)
nécessiterait des connecteurs/abonnements officiels.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VeilleReglementaire(Base, TimestampMixin):
    __tablename__ = "veille_reglementaire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titre: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(80), default="")          # CNCC, H2A, IAASB, OHADA…
    referentiel: Mapped[str] = mapped_column(String(40), default="TRANSVERSE")
    reference: Mapped[str] = mapped_column(String(80), default="")       # ex. NEP 240, ISA 600
    date_publication: Mapped[date | None] = mapped_column(Date, nullable=True)
    resume: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(300), default="")
    impact: Mapped[str] = mapped_column(String(20), default="moyen")     # faible | moyen | fort
    lu: Mapped[bool] = mapped_column(Boolean, default=False)
