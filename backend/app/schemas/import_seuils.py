"""Schémas Phase 3 — Import FEC et seuils."""
from __future__ import annotations

from pydantic import BaseModel


class ImportFECOut(BaseModel):
    exercice: str
    nb_comptes: int
    nb_ecritures: int
    total_debit: float
    total_credit: float
    equilibre: bool
    resultat_net: float
    chiffre_affaires: float
    capitaux_propres: float


class ParamsSeuilsIn(BaseModel):
    pct_resultat_net: float = 0.05
    pct_chiffre_affaires: float = 0.01
    pct_capitaux_propres: float = 0.05
    ratio_planification: float = 0.50
    ratio_remontee: float = 0.05
    # Bases optionnelles : si absentes, dérivées de la balance N importée.
    resultat_net: float | None = None
    chiffre_affaires: float | None = None
    capitaux_propres: float | None = None


class SeuilsOut(BaseModel):
    seuil_signification: float
    seuil_planification: float
    seuil_remontee: float
    base_retenue: str
    candidats: dict[str, float]
