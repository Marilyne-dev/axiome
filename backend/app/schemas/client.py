"""Schémas Module 2 — Clients et entités rattachées."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    raison_sociale: str = Field(min_length=1)
    identifiant_legal: str = ""
    pays: str = "France"
    secteur: str = ""
    groupe_id: int | None = None


class ClientUpdate(BaseModel):
    raison_sociale: str | None = None
    identifiant_legal: str | None = None
    pays: str | None = None
    secteur: str | None = None
    is_archived: bool | None = None


class ClientOut(BaseModel):
    id: int
    raison_sociale: str
    identifiant_legal: str
    pays: str
    secteur: str
    is_archived: bool

    model_config = {"from_attributes": True}


class ContactIn(BaseModel):
    nom: str
    fonction: str = ""
    email: str = ""
    telephone: str = ""


class DirigeantIn(BaseModel):
    nom: str
    mandat: str = ""
    date_nomination: str = ""


class CompteBancaireIn(BaseModel):
    banque: str
    iban: str = ""
    devise: str = "EUR"
