"""Schémas Module 4 — Planification."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PlanUpsert(BaseModel):
    date_debut: date | None = None
    date_fin: date | None = None
    approche: str = ""
    honoraires: float = 0.0
    devise: str = "EUR"


class JalonIn(BaseModel):
    libelle: str
    echeance: date | None = None
    statut: str = "a_faire"


class AffectationIn(BaseModel):
    user_id: int
    role_mission: str = "collaborateur"
    heures_estimees: float = 0.0


class LigneBudgetIn(BaseModel):
    poste: str
    montant: float = 0.0
    devise: str = "EUR"
