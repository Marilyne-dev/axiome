"""Schémas Module 1 — Administration : gestion des utilisateurs et du cabinet."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nom_complet: str = ""
    roles: list[str] = Field(default_factory=list)  # codes de rôles
    lang: str = "fr"


class UserUpdate(BaseModel):
    nom_complet: str | None = None
    is_active: bool | None = None
    roles: list[str] | None = None
    lang: str | None = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    nom_complet: str
    is_active: bool
    roles: list[str]
    lang: str

    model_config = {"from_attributes": True}


class CabinetUpdate(BaseModel):
    nom: str | None = None
    pays: str | None = None
    devise_defaut: str | None = None
    referentiel_defaut: str | None = None
