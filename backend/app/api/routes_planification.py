"""Module 4 — Planification : plan, jalons, équipe, budget."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.mission import Mission
from app.models.planification import AffectationEquipe, Jalon, LigneBudget, PlanMission
from app.models.user import User
from app.schemas.planification import AffectationIn, JalonIn, LigneBudgetIn, PlanUpsert
from app.services.audit_service import journaliser

router = APIRouter(prefix="/missions/{mission_id}/planification", tags=["planification"])


def _get_plan(db: Session, mission_id: int) -> PlanMission:
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    plan = db.query(PlanMission).filter_by(mission_id=mission_id).first()
    if not plan:
        plan = PlanMission(mission_id=mission_id)
        db.add(plan); db.flush()
    return plan


@router.get("")
def get_plan(mission_id: int, db: Session = Depends(get_db),
             _=Depends(require_permission("mission:read"))) -> dict:
    plan = _get_plan(db, mission_id)
    db.commit()
    return {
        "id": plan.id, "approche": plan.approche, "honoraires": plan.honoraires, "devise": plan.devise,
        "date_debut": str(plan.date_debut) if plan.date_debut else None,
        "date_fin": str(plan.date_fin) if plan.date_fin else None,
        "jalons": [{"id": j.id, "libelle": j.libelle, "statut": j.statut,
                    "echeance": str(j.echeance) if j.echeance else None} for j in plan.jalons],
        "equipe": [{"id": a.id, "user_id": a.user_id, "role_mission": a.role_mission,
                    "heures_estimees": a.heures_estimees} for a in plan.equipe],
        "budget": [{"id": b.id, "poste": b.poste, "montant": b.montant, "devise": b.devise} for b in plan.budget],
        "total_budget": sum(b.montant for b in plan.budget),
        "total_heures": sum(a.heures_estimees for a in plan.equipe),
    }


@router.put("")
def upsert_plan(mission_id: int, data: PlanUpsert, db: Session = Depends(get_db),
                user: User = Depends(require_permission("mission:write"))) -> dict:
    plan = _get_plan(db, mission_id)
    for champ, valeur in data.model_dump(exclude_unset=True).items():
        setattr(plan, champ, valeur)
    journaliser(db, user_id=user.id, action="plan.upsert", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(plan)
    return {"id": plan.id, "approche": plan.approche, "honoraires": plan.honoraires, "devise": plan.devise}


@router.post("/jalons", status_code=status.HTTP_201_CREATED)
def add_jalon(mission_id: int, data: JalonIn, db: Session = Depends(get_db),
              user: User = Depends(require_permission("mission:write"))) -> dict:
    plan = _get_plan(db, mission_id)
    j = Jalon(plan_id=plan.id, **data.model_dump())
    db.add(j)
    journaliser(db, user_id=user.id, action="jalon.add", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(j)
    return {"id": j.id, "libelle": j.libelle, "statut": j.statut}


@router.post("/equipe", status_code=status.HTTP_201_CREATED)
def add_affectation(mission_id: int, data: AffectationIn, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("mission:write"))) -> dict:
    plan = _get_plan(db, mission_id)
    if not db.get(User, data.user_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Collaborateur inconnu")
    a = AffectationEquipe(plan_id=plan.id, **data.model_dump())
    db.add(a)
    journaliser(db, user_id=user.id, action="equipe.affecter", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(a)
    return {"id": a.id, "user_id": a.user_id, "role_mission": a.role_mission, "heures_estimees": a.heures_estimees}


@router.post("/budget", status_code=status.HTTP_201_CREATED)
def add_ligne_budget(mission_id: int, data: LigneBudgetIn, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("mission:write"))) -> dict:
    plan = _get_plan(db, mission_id)
    b = LigneBudget(plan_id=plan.id, **data.model_dump())
    db.add(b)
    journaliser(db, user_id=user.id, action="budget.add", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(b)
    return {"id": b.id, "poste": b.poste, "montant": b.montant, "devise": b.devise}
