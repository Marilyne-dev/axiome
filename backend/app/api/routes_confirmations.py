"""Module 12 — Confirmations externes (circularisations) + relances."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import Confirmation
from app.models.mission import Mission
from app.models.user import User
from app.schemas.audit_phase4 import ConfirmationIn
from app.services.audit_service import journaliser

router = APIRouter(prefix="/missions/{mission_id}/confirmations", tags=["confirmations"])

TYPES_TIERS = {"banque", "client", "fournisseur", "avocat", "assurance", "fiscal", "social"}


def _assert_mission(db: Session, mission_id: int) -> None:
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")


@router.get("")
def lister(mission_id: int, db: Session = Depends(get_db),
           _=Depends(require_permission("mission:read"))) -> list[dict]:
    _assert_mission(db, mission_id)
    confs = db.query(Confirmation).filter_by(mission_id=mission_id).all()
    return [{"id": c.id, "tiers": c.tiers, "type_tiers": c.type_tiers, "statut": c.statut} for c in confs]


@router.post("", status_code=status.HTTP_201_CREATED)
def creer(mission_id: int, data: ConfirmationIn, db: Session = Depends(get_db),
          user: User = Depends(require_permission("mission:write"))) -> dict:
    _assert_mission(db, mission_id)
    if data.type_tiers not in TYPES_TIERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Type de tiers invalide (attendu : {sorted(TYPES_TIERS)})")
    c = Confirmation(mission_id=mission_id, tiers=data.tiers, type_tiers=data.type_tiers, statut="envoyee")
    db.add(c)
    journaliser(db, user_id=user.id, action="confirmation.create", objet="mission", detail=data.tiers)
    db.commit(); db.refresh(c)
    return {"id": c.id, "tiers": c.tiers, "type_tiers": c.type_tiers, "statut": c.statut}


@router.post("/{conf_id}/relancer")
def relancer(mission_id: int, conf_id: int, db: Session = Depends(get_db),
             user: User = Depends(require_permission("mission:write"))) -> dict:
    c = db.get(Confirmation, conf_id)
    if not c or c.mission_id != mission_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Confirmation introuvable")
    if c.statut == "recue":
        raise HTTPException(status.HTTP_409_CONFLICT, "Confirmation déjà reçue : relance inutile.")
    c.statut = "relancee"
    journaliser(db, user_id=user.id, action="confirmation.relancer", objet="mission", detail=str(conf_id))
    db.commit()
    return {"id": c.id, "statut": c.statut}
