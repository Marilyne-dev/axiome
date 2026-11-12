"""Module 27 — Calcul et enregistrement des seuils de mission."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import Threshold
from app.models.mission import Mission
from app.models.user import User
from app.schemas.seuils import BasesSeuils, SeuilsOut
from app.services.audit_service import journaliser
from app.services.seuils_service import calculer

router = APIRouter(prefix="/missions/{mission_id}/seuils", tags=["seuils"])


@router.post("", response_model=SeuilsOut)
def calculer_seuils(mission_id: int, data: BasesSeuils, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("mission:write"))) -> SeuilsOut:
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    res = calculer(
        bases={"resultat_net": data.resultat_net, "chiffre_affaires": data.chiffre_affaires,
               "capitaux_propres": data.capitaux_propres},
        taux=data.taux, ratio_planification=data.ratio_planification, ratio_remontee=data.ratio_remontee,
    )
    # Enregistrer (upsert) sur la mission
    seuil = db.query(Threshold).filter_by(mission_id=mission_id).first() or Threshold(mission_id=mission_id)
    seuil.seuil_signification = res.seuil_signification
    seuil.seuil_planification = res.seuil_planification
    seuil.seuil_remontee = res.seuil_remontee
    seuil.base_retenue = res.base_retenue
    db.add(seuil)
    journaliser(db, user_id=user.id, action="seuils.calculer", objet="mission", detail=res.base_retenue)
    db.commit()
    return SeuilsOut(**res.__dict__)


@router.get("", response_model=SeuilsOut)
def lire_seuils(mission_id: int, db: Session = Depends(get_db),
                _=Depends(require_permission("mission:read"))) -> SeuilsOut:
    s = db.query(Threshold).filter_by(mission_id=mission_id).first()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Seuils non calculés")
    return SeuilsOut(seuil_signification=s.seuil_signification, seuil_planification=s.seuil_planification,
                     seuil_remontee=s.seuil_remontee, base_retenue=s.base_retenue, details={})
