"""Module 3 — Acceptation et maintien de la mission.

La décision d'accepter/refuser est un acte humain habilité (associé signataire).
L'outil calcule un risque indicatif et trace la décision motivée.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.acceptation import Acceptation, LettreMission
from app.models.mission import Mission
from app.models.user import User
from app.schemas.acceptation import AcceptationOut, AcceptationUpsert, DecisionIn
from app.services.audit_service import journaliser

router = APIRouter(prefix="/missions/{mission_id}/acceptation", tags=["acceptation"])


def _get_mission(db: Session, mission_id: int) -> Mission:
    m = db.get(Mission, mission_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return m


def _get_or_create(db: Session, mission_id: int) -> Acceptation:
    acc = db.query(Acceptation).filter_by(mission_id=mission_id).first()
    if not acc:
        acc = Acceptation(mission_id=mission_id)
        db.add(acc)
        db.flush()
    return acc


@router.get("", response_model=AcceptationOut)
def get_acceptation(mission_id: int, db: Session = Depends(get_db),
                    _=Depends(require_permission("mission:read"))) -> Acceptation:
    _get_mission(db, mission_id)
    return _get_or_create(db, mission_id)


@router.put("", response_model=AcceptationOut)
def upsert_acceptation(
    mission_id: int, data: AcceptationUpsert, db: Session = Depends(get_db),
    user: User = Depends(require_permission("mission:write")),
) -> Acceptation:
    _get_mission(db, mission_id)
    acc = _get_or_create(db, mission_id)
    acc.independance_ok = data.independance_ok
    acc.conflit_interet = data.conflit_interet
    acc.kyc_ok = data.kyc_ok
    acc.continuite_exploitation_ok = data.continuite_exploitation_ok
    acc.niveau_risque_global = data.niveau_risque_global
    acc.questionnaire = json.dumps(data.questionnaire, ensure_ascii=False)
    journaliser(db, user_id=user.id, action="acceptation.upsert", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(acc)
    return acc


@router.post("/decision", response_model=AcceptationOut)
def decider(
    mission_id: int, data: DecisionIn, db: Session = Depends(get_db),
    user: User = Depends(require_permission("mission:write")),
) -> Acceptation:
    """Enregistre la décision motivée. Refus interdit si conflit non levé et accepté."""
    if data.decision not in {"acceptee", "refusee"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Décision invalide")
    _get_mission(db, mission_id)
    acc = _get_or_create(db, mission_id)
    # Garde-fou métier : on ne peut accepter avec un conflit d'intérêt non traité.
    if data.decision == "acceptee" and acc.conflit_interet:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Acceptation impossible : conflit d'intérêt à lever d'abord.")
    acc.decision = data.decision
    acc.motivation = data.motivation
    acc.decideur_id = user.id
    # Répercuter sur le statut de la mission.
    mission = _get_mission(db, mission_id)
    mission.statut = "planification" if data.decision == "acceptee" else "refusee"
    journaliser(db, user_id=user.id, action=f"acceptation.{data.decision}", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(acc)
    return acc


@router.post("/lettre-mission")
def generer_lettre(mission_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("mission:write"))) -> dict:
    """Génère un brouillon de lettre de mission à partir des données de la mission."""
    mission = _get_mission(db, mission_id)
    acc = _get_or_create(db, mission_id)
    if acc.decision != "acceptee":
        raise HTTPException(status.HTTP_409_CONFLICT, "Mission non acceptée : lettre indisponible.")
    corps = (
        f"Lettre de mission — {mission.intitule}\n"
        f"Référentiel : {mission.referentiel} · Pays : {mission.pays} · Devise : {mission.devise}\n"
        f"Exercice : {mission.exercice}\n\n"
        "Objet : mission de commissariat aux comptes conformément aux normes applicables."
    )
    lettre = db.query(LettreMission).filter_by(acceptation_id=acc.id).first()
    if not lettre:
        lettre = LettreMission(acceptation_id=acc.id, reference=f"LM-{mission_id}", corps=corps, statut="brouillon")
        db.add(lettre)
    else:
        lettre.corps = corps
    journaliser(db, user_id=user.id, action="lettre_mission.generer", objet="mission", detail=str(mission_id))
    db.commit(); db.refresh(lettre)
    return {"id": lettre.id, "reference": lettre.reference, "statut": lettre.statut, "corps": lettre.corps}
