"""Module 7 — Cartographie des risques : CRUD, heat map, priorisation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import RiskItem
from app.models.mission import Mission
from app.models.user import User
from app.schemas.audit_phase4 import RiskIn, RiskOut
from app.services.audit_service import journaliser
from app.services.risque_service import heatmap, niveau, prioriser

router = APIRouter(prefix="/missions/{mission_id}/risques", tags=["risques"])


def _assert_mission(db: Session, mission_id: int) -> None:
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")


@router.get("", response_model=list[RiskOut])
def lister(mission_id: int, db: Session = Depends(get_db),
           _=Depends(require_permission("mission:read"))) -> list[RiskItem]:
    _assert_mission(db, mission_id)
    risques = db.query(RiskItem).filter_by(mission_id=mission_id).all()
    return prioriser(risques)  # priorisation automatique (score décroissant)


@router.post("", response_model=RiskOut, status_code=status.HTTP_201_CREATED)
def ajouter(mission_id: int, data: RiskIn, db: Session = Depends(get_db),
            user: User = Depends(require_permission("mission:write"))) -> RiskItem:
    _assert_mission(db, mission_id)
    r = RiskItem(mission_id=mission_id, **data.model_dump())
    db.add(r)
    journaliser(db, user_id=user.id, action="risque.add", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(r)
    return r


@router.get("/heatmap")
def carte_chaleur(mission_id: int, db: Session = Depends(get_db),
                  _=Depends(require_permission("mission:read"))) -> dict:
    _assert_mission(db, mission_id)
    risques = db.query(RiskItem).filter_by(mission_id=mission_id).all()
    top = prioriser(risques)[:5]
    return {
        **heatmap(risques),
        "prioritaires": [{"id": r.id, "libelle": r.libelle, "score": r.score, "niveau": niveau(r.score)} for r in top],
        "total": len(risques),
    }
