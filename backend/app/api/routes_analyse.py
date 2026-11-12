"""Modules 6 & 15 — Analyse financière et revue analytique (depuis la balance)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import Threshold
from app.models.balance import LigneBalance
from app.models.mission import Mission
from app.services.analyse_service import analyse_complete
from app.services.revue_service import revue_analytique

router = APIRouter(prefix="/missions/{mission_id}", tags=["analyse"])


def _lignes(db: Session, mission_id: int) -> list[LigneBalance]:
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    lignes = db.query(LigneBalance).filter_by(mission_id=mission_id).all()
    if not lignes:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucune balance importée pour cette mission.")
    return lignes


@router.get("/analyse-financiere")
def analyse(mission_id: int, db: Session = Depends(get_db),
            _=Depends(require_permission("mission:read"))) -> dict:
    """Module 6 : agrégats de structure (FRNG, BFR, trésorerie nette) et ratios."""
    return analyse_complete(_lignes(db, mission_id))


@router.get("/revue-analytique")
def revue(mission_id: int, seuil: float | None = None, db: Session = Depends(get_db),
          _=Depends(require_permission("mission:read"))) -> dict:
    """Module 15 : comparaison N/N-1. Seuil par défaut = seuil de remontée calculé."""
    lignes = _lignes(db, mission_id)
    if seuil is None:
        t = db.query(Threshold).filter_by(mission_id=mission_id).first()
        seuil = t.seuil_remontee if t else 0.0
    return revue_analytique(lignes, seuil=seuil or 0.0)
