"""Modules 14/16 — Endpoint de l'assistant IA."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.ia_service import assister, ia_disponible

router = APIRouter(prefix="/ia", tags=["assistant_ia"])


class AssistIn(BaseModel):
    prompt: str
    contexte: str = ""


@router.get("/statut")
def statut(_: User = Depends(get_current_user)) -> dict:
    return {"disponible": ia_disponible()}


@router.post("/assister")
def assister_ia(data: AssistIn, _: User = Depends(get_current_user)) -> dict:
    """Aide rédactionnelle IA (l'humain valide toujours)."""
    return assister(data.prompt, data.contexte)
