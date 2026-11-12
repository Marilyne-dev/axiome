"""Module 10 — Feuilles de travail : CRUD, notes, validation (versionnable)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import WorkingPaper
from app.models.mission import Cycle
from app.models.user import User
from app.schemas.audit_phase4 import FeuilleIn
from app.services.audit_service import journaliser

router = APIRouter(prefix="/cycles/{cycle_id}/feuilles", tags=["feuilles_de_travail"])


def _assert_cycle(db: Session, cycle_id: int) -> None:
    if not db.get(Cycle, cycle_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")


@router.get("")
def lister(cycle_id: int, db: Session = Depends(get_db),
           _=Depends(require_permission("cycle:read"))) -> list[dict]:
    _assert_cycle(db, cycle_id)
    fts = db.query(WorkingPaper).filter_by(cycle_id=cycle_id).all()
    return [{"id": f.id, "reference": f.reference, "titre": f.titre, "statut": f.statut} for f in fts]


@router.post("", status_code=status.HTTP_201_CREATED)
def creer(cycle_id: int, data: FeuilleIn, db: Session = Depends(get_db),
          user: User = Depends(require_permission("cycle:write"))) -> dict:
    _assert_cycle(db, cycle_id)
    f = WorkingPaper(cycle_id=cycle_id, **data.model_dump())
    db.add(f)
    journaliser(db, user_id=user.id, action="feuille.create", objet="cycle", detail=str(cycle_id))
    db.commit(); db.refresh(f)
    return {"id": f.id, "reference": f.reference, "titre": f.titre, "statut": f.statut}


@router.patch("/{feuille_id}/valider")
def valider(cycle_id: int, feuille_id: int, db: Session = Depends(get_db),
            user: User = Depends(require_permission("cycle:write"))) -> dict:
    f = db.get(WorkingPaper, feuille_id)
    if not f or f.cycle_id != cycle_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feuille introuvable")
    f.statut = "validee"
    journaliser(db, user_id=user.id, action="feuille.valider", objet="cycle", detail=str(feuille_id))
    db.commit()
    return {"id": f.id, "statut": f.statut}
