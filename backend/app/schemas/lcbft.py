"""Schémas Module 13 bis — LCB-FT."""
from __future__ import annotations

from pydantic import BaseModel


class DossierIn(BaseModel):
    client_id: int
    ubo: str = ""            # bénéficiaires effectifs


class ClassificationIn(BaseModel):
    pays_a_risque: bool = False
    activite_especes: bool = False
    ppe: bool = False
    structure_complexe: bool = False
    relation_a_distance: bool = False


class ScreeningIn(BaseModel):
    nom: str


class DeclarationIn(BaseModel):
    motif: str
