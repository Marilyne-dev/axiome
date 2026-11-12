"""Module 8 — Contrôle interne (COSO) : points de contrôle et faiblesses."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.controle_interne import COMPOSANTES_COSO, ControleInterne, Faiblesse
from app.models.mission import Cycle
from app.models.user import User
from app.schemas.audit_phase4 import ControleIn, FaiblesseIn
from app.services.audit_service import journaliser

router = APIRouter(prefix="/cycles/{cycle_id}/controle-interne", tags=["controle_interne"])


def _assert_cycle(db: Session, cycle_id: int) -> None:
    if not db.get(Cycle, cycle_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")


@router.get("")
def lister(cycle_id: int, db: Session = Depends(get_db),
           _=Depends(require_permission("cycle:read"))) -> list[dict]:
    _assert_cycle(db, cycle_id)
    ctrls = db.query(ControleInterne).filter_by(cycle_id=cycle_id).all()
    return [{"id": c.id, "intitule": c.intitule, "composante_coso": c.composante_coso,
             "conclusion": c.conclusion,
             "faiblesses": [{"id": f.id, "libelle": f.libelle, "gravite": f.gravite} for f in c.faiblesses]}
            for c in ctrls]


@router.post("", status_code=status.HTTP_201_CREATED)
def creer(cycle_id: int, data: ControleIn, db: Session = Depends(get_db),
          user: User = Depends(require_permission("cycle:write"))) -> dict:
    _assert_cycle(db, cycle_id)
    if data.composante_coso not in COMPOSANTES_COSO:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Composante COSO invalide (attendu : {list(COMPOSANTES_COSO)})")
    c = ControleInterne(cycle_id=cycle_id, **data.model_dump())
    db.add(c)
    journaliser(db, user_id=user.id, action="ci.add", objet="cycle", detail=str(cycle_id))
    db.commit(); db.refresh(c)
    return {"id": c.id, "intitule": c.intitule, "conclusion": c.conclusion}


@router.post("/{controle_id}/faiblesses", status_code=status.HTTP_201_CREATED)
def ajouter_faiblesse(cycle_id: int, controle_id: int, data: FaiblesseIn, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("cycle:write"))) -> dict:
    ctrl = db.get(ControleInterne, controle_id)
    if not ctrl or ctrl.cycle_id != cycle_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contrôle introuvable")
    f = Faiblesse(controle_id=controle_id, **data.model_dump())
    ctrl.conclusion = "deficient"  # une faiblesse rend le contrôle déficient
    db.add(f)
    journaliser(db, user_id=user.id, action="ci.faiblesse", objet="cycle", detail=str(cycle_id))
    db.commit(); db.refresh(f)
    return {"id": f.id, "libelle": f.libelle, "gravite": f.gravite}
