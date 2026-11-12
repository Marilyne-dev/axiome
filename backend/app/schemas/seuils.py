"""Schémas Module 27 — Seuils."""
from __future__ import annotations

from pydantic import BaseModel, Field


class BasesSeuils(BaseModel):
    resultat_net: float = 0.0
    chiffre_affaires: float = 0.0
    capitaux_propres: float = 0.0
    # Taux et ratios paramétrables (optionnels)
    taux: dict[str, float] | None = None
    ratio_planification: float = Field(default=0.75, ge=0.5, le=0.75)
    ratio_remontee: float = Field(default=0.05, ge=0.05, le=0.10)


class SeuilsOut(BaseModel):
    seuil_signification: float
    seuil_planification: float
    seuil_remontee: float
    base_retenue: str
    details: dict
