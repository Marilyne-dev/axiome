"""Schémas Module 3 — Acceptation/maintien."""
from __future__ import annotations

from pydantic import BaseModel


class AcceptationUpsert(BaseModel):
    independance_ok: bool = False
    conflit_interet: bool = False
    kyc_ok: bool = False
    continuite_exploitation_ok: bool = True
    niveau_risque_global: str = "standard"
    questionnaire: dict = {}


class DecisionIn(BaseModel):
    decision: str          # acceptee | refusee
    motivation: str = ""


class AcceptationOut(BaseModel):
    id: int
    mission_id: int
    independance_ok: bool
    conflit_interet: bool
    kyc_ok: bool
    continuite_exploitation_ok: bool
    niveau_risque_global: str
    decision: str
    motivation: str

    model_config = {"from_attributes": True}
