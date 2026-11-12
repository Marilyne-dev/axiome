"""Module 9 — Programme d'audit : génération par cycle + procédures."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.mission import Cycle
from app.models.programme import ProcedureAudit, ProgrammeAudit
from app.models.user import User
from app.schemas.audit_phase4 import ProcedureIn
from app.services.audit_service import journaliser

router = APIRouter(prefix="/cycles/{cycle_id}/programme", tags=["programme"])

# Procédures standard proposées par cycle (base, personnalisable ensuite).
PROCEDURES_STANDARD: dict[str, list[tuple[str, str, str]]] = {
    "TRESORERIE": [
        ("TR-1", "Rapprochement bancaire de clôture", "exhaustivite"),
        ("TR-2", "Circularisation des banques", "existence"),
        ("TR-3", "Contrôle des chèques/virements en suspens", "exhaustivite"),
    ],
    "EMPRUNTS": [
        ("EMP-1", "Vérification des échéanciers d'emprunt", "exactitude"),
        ("EMP-2", "Recalcul des intérêts courus", "exactitude"),
        ("EMP-3", "Confirmation auprès des établissements prêteurs", "existence"),
    ],
    "VENTES": [
        ("VE-1", "Circularisation des clients", "existence"),
        ("VE-2", "Test de césure (cut-off) des ventes", "rattachement"),
    ],
    "ACHATS": [
        ("AC-1", "Circularisation des fournisseurs", "existence"),
        ("AC-2", "Recherche de factures non parvenues (FNP)", "exhaustivite"),
    ],
}


def _get_programme(db: Session, cycle_id: int) -> ProgrammeAudit:
    cycle = db.get(Cycle, cycle_id)
    if not cycle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    prog = db.query(ProgrammeAudit).filter_by(cycle_id=cycle_id).first()
    if not prog:
        prog = ProgrammeAudit(cycle_id=cycle_id, intitule=f"Programme {cycle.libelle}")
        db.add(prog); db.flush()
    return prog


@router.get("")
def obtenir(cycle_id: int, db: Session = Depends(get_db),
            _=Depends(require_permission("cycle:read"))) -> dict:
    prog = _get_programme(db, cycle_id)
    db.commit()
    return {"id": prog.id, "intitule": prog.intitule, "statut": prog.statut,
            "procedures": [{"id": p.id, "reference": p.reference, "libelle": p.libelle,
                            "assertion": p.assertion, "fait": p.fait} for p in prog.procedures]}


@router.post("/generer")
def generer(cycle_id: int, db: Session = Depends(get_db),
            user: User = Depends(require_permission("cycle:write"))) -> dict:
    """Génère automatiquement les procédures standard selon le code du cycle."""
    cycle = db.get(Cycle, cycle_id)
    if not cycle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    prog = _get_programme(db, cycle_id)
    modele = PROCEDURES_STANDARD.get(cycle.code.upper(), [])
    existantes = {p.reference for p in prog.procedures}
    ajoutees = 0
    for ref, lib, assertion in modele:
        if ref not in existantes:
            db.add(ProcedureAudit(programme_id=prog.id, reference=ref, libelle=lib, assertion=assertion))
            ajoutees += 1
    journaliser(db, user_id=user.id, action="programme.generer", objet="cycle", detail=cycle.code)
    db.commit()
    return {"programme_id": prog.id, "procedures_ajoutees": ajoutees, "cycle": cycle.code}


@router.post("/procedures", status_code=status.HTTP_201_CREATED)
def ajouter_procedure(cycle_id: int, data: ProcedureIn, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("cycle:write"))) -> dict:
    prog = _get_programme(db, cycle_id)
    p = ProcedureAudit(programme_id=prog.id, **data.model_dump())
    db.add(p)
    journaliser(db, user_id=user.id, action="procedure.add", objet="cycle", detail=str(cycle_id))
    db.commit(); db.refresh(p)
    return {"id": p.id, "reference": p.reference, "libelle": p.libelle}


@router.patch("/procedures/{procedure_id}/fait")
def marquer_fait(cycle_id: int, procedure_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("cycle:write"))) -> dict:
    p = db.get(ProcedureAudit, procedure_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Procédure introuvable")
    p.fait = True
    p.assignee_id = user.id
    db.commit()
    return {"id": p.id, "fait": True}
