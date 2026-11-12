"""Module 13 — Détection de fraude : Benford + indicateurs sur la balance."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.balance import LigneBalance
from app.models.mission import Mission
from app.services.benford_service import analyse_benford, indicateurs_fraude

router = APIRouter(prefix="/missions/{mission_id}/fraude", tags=["fraude"])


def _montants(db: Session, mission_id: int) -> list[float]:
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    lignes = db.query(LigneBalance).filter_by(mission_id=mission_id).all()
    if not lignes:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucune balance importée.")
    # On analyse les soldes N non nuls (les mouvements pourraient être analysés de même).
    return [lb.solde_n for lb in lignes if lb.solde_n]


@router.get("/benford")
def benford(mission_id: int, db: Session = Depends(get_db),
            _=Depends(require_permission("mission:read"))) -> dict:
    """Analyse de la loi de Benford (1er chiffre) sur les soldes de la balance."""
    return analyse_benford(_montants(db, mission_id))


@router.get("/indicateurs")
def indicateurs(mission_id: int, db: Session = Depends(get_db),
                _=Depends(require_permission("mission:read"))) -> dict:
    """Indicateurs complémentaires : nombres ronds, montants dupliqués."""
    return indicateurs_fraude(_montants(db, mission_id))
