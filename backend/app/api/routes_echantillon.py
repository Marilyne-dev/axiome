"""Module 11 — Échantillonnage : calcul de taille (aide à la décision) + éléments."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import Sample
from app.models.echantillonnage import SampleItem
from app.models.mission import Cycle
from app.models.user import User
from app.schemas.audit_phase4 import EchantillonIn, SampleItemIn
from app.services.audit_service import journaliser
from app.services.echantillon_service import taille_attributs, taille_mus

router = APIRouter(prefix="/cycles/{cycle_id}/echantillons", tags=["echantillonnage"])


def _assert_cycle(db: Session, cycle_id: int) -> None:
    if not db.get(Cycle, cycle_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")


@router.post("", status_code=status.HTTP_201_CREATED)
def creer(cycle_id: int, data: EchantillonIn, db: Session = Depends(get_db),
          user: User = Depends(require_permission("cycle:write"))) -> dict:
    """Crée un échantillon en calculant une taille indicative selon la méthode."""
    _assert_cycle(db, cycle_id)
    if data.methode == "mus":
        taille = taille_mus(data.valeur_population, data.seuil_tolerable, data.confiance)
    elif data.methode == "attributs":
        taille = taille_attributs(data.taux_tolerable, data.confiance)
    else:  # aléatoire / dirigé : taille laissée au jugement, 0 par défaut
        taille = 0
    s = Sample(cycle_id=cycle_id, methode=data.methode, taille=taille)
    db.add(s)
    journaliser(db, user_id=user.id, action="echantillon.create", objet="cycle", detail=data.methode)
    db.commit(); db.refresh(s)
    return {"id": s.id, "methode": s.methode, "taille": s.taille,
            "note": "Taille indicative (NEP 530 / ISA 530) — à ajuster selon le jugement professionnel."}


@router.post("/{sample_id}/items", status_code=status.HTTP_201_CREATED)
def ajouter_item(cycle_id: int, sample_id: int, data: SampleItemIn, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("cycle:write"))) -> dict:
    s = db.get(Sample, sample_id)
    if not s or s.cycle_id != cycle_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Échantillon introuvable")
    item = SampleItem(sample_id=sample_id, **data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "reference_piece": item.reference_piece, "montant": item.montant}
