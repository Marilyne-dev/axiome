"""Schémas Phase 4 — Modules 7 à 12."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --- Module 7 : Risques ---
class RiskIn(BaseModel):
    libelle: str = Field(min_length=1)
    categorie: str = "inherent"       # inherent|controle|fraude|continuite|conformite
    probabilite: int = Field(default=1, ge=1, le=5)
    impact: int = Field(default=1, ge=1, le=5)


class RiskOut(BaseModel):
    id: int
    libelle: str
    categorie: str
    probabilite: int
    impact: int
    score: int
    model_config = {"from_attributes": True}


# --- Module 8 : Contrôle interne ---
class ControleIn(BaseModel):
    intitule: str
    composante_coso: str = "activites_controle"
    description: str = ""
    walkthrough: str = ""
    conclusion: str = "a_tester"


class FaiblesseIn(BaseModel):
    libelle: str
    gravite: str = "mineure"
    recommandation: str = ""


# --- Module 9 : Programme ---
class ProcedureIn(BaseModel):
    libelle: str
    reference: str = ""
    assertion: str = ""


# --- Module 10 : Feuilles de travail ---
class FeuilleIn(BaseModel):
    reference: str = ""
    titre: str = ""
    contenu: str = ""


# --- Module 11 : Échantillonnage ---
class EchantillonIn(BaseModel):
    methode: str = "mus"              # mus|attributs|aleatoire|dirige
    valeur_population: float = 0.0
    seuil_tolerable: float = 0.0
    taux_tolerable: float = 0.05
    confiance: float = 0.95


class SampleItemIn(BaseModel):
    reference_piece: str = ""
    montant: float = 0.0
    devise: str = "EUR"


# --- Module 12 : Confirmations ---
class ConfirmationIn(BaseModel):
    tiers: str
    type_tiers: str = "banque"        # banque|client|fournisseur|avocat|assurance|fiscal|social
