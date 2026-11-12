"""Module 13 bis — LCB-FT (confidentiel). Accès restreint au correspondant + journalisé."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_lcbft
from app.core.database import get_db
from app.models.client import Client
from app.models.lcbft import DeclarationSoupcon, DossierLCBFT
from app.models.user import User
from app.schemas.lcbft import ClassificationIn, DeclarationIn, DossierIn, ScreeningIn
from app.services.audit_service import journaliser
from app.services.lcbft_service import classifier_risque, screening

router = APIRouter(prefix="/lcbft", tags=["lcbft (confidentiel)"])


def _tracer(db: Session, user: User, action: str, detail: str, request: Request) -> None:
    """Journalise TOUT accès LCB-FT (traçabilité confidentielle)."""
    journaliser(db, user_id=user.id, action=f"lcbft.{action}", objet="lcbft", detail=detail,
                ip=request.client.host if request.client else "")


@router.post("/dossiers", status_code=status.HTTP_201_CREATED)
def creer_dossier(data: DossierIn, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_lcbft)) -> dict:
    if not db.get(Client, data.client_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client introuvable")
    dossier = db.query(DossierLCBFT).filter_by(client_id=data.client_id).first()
    if not dossier:
        dossier = DossierLCBFT(client_id=data.client_id, ubo=data.ubo)
        db.add(dossier); db.flush()
    else:
        dossier.ubo = data.ubo or dossier.ubo
    _tracer(db, user, "dossier.upsert", f"client={data.client_id}", request)
    db.commit(); db.refresh(dossier)
    return {"id": dossier.id, "client_id": dossier.client_id,
            "niveau_risque": dossier.niveau_risque, "statut": dossier.statut}


@router.get("/dossiers/{dossier_id}")
def lire_dossier(dossier_id: int, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_lcbft)) -> dict:
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    _tracer(db, user, "dossier.read", f"dossier={dossier_id}", request); db.commit()
    return {"id": d.id, "client_id": d.client_id, "niveau_risque": d.niveau_risque,
            "ppe": bool(d.ppe), "statut": d.statut,
            "nb_declarations": len(d.declarations)}


@router.post("/dossiers/{dossier_id}/classification")
def classifier(dossier_id: int, data: ClassificationIn, request: Request,
               db: Session = Depends(get_db), user: User = Depends(require_lcbft)) -> dict:
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    res = classifier_risque(**data.model_dump())
    d.niveau_risque = res["niveau_risque"]
    d.ppe = 1 if data.ppe else 0
    _tracer(db, user, "classification", f"dossier={dossier_id} niveau={res['niveau_risque']}", request)
    db.commit()
    return res


@router.post("/screening")
def screening_nom(data: ScreeningIn, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_lcbft)) -> dict:
    res = screening(data.nom)
    _tracer(db, user, "screening", f"nom={data.nom} vigilance={res['vigilance']}", request); db.commit()
    return res


@router.post("/dossiers/{dossier_id}/declarations", status_code=status.HTTP_201_CREATED)
def creer_declaration(dossier_id: int, data: DeclarationIn, request: Request,
                      db: Session = Depends(get_db), user: User = Depends(require_lcbft)) -> dict:
    """Déclaration de soupçon TRACFIN — CONFIDENTIEL, non divulgable au client."""
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    decl = DeclarationSoupcon(dossier_id=dossier_id, redacteur_id=user.id,
                              reference=f"DS-{dossier_id}-{len(d.declarations)+1}",
                              motif=data.motif, statut="brouillon")
    db.add(decl)
    _tracer(db, user, "declaration.create", f"dossier={dossier_id}", request)
    db.commit(); db.refresh(decl)
    return {"id": decl.id, "reference": decl.reference, "statut": decl.statut}


@router.get("/dossiers/{dossier_id}/declarations")
def lister_declarations(dossier_id: int, request: Request, db: Session = Depends(get_db),
                        user: User = Depends(require_lcbft)) -> list[dict]:
    d = db.get(DossierLCBFT, dossier_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable")
    _tracer(db, user, "declaration.list", f"dossier={dossier_id}", request); db.commit()
    return [{"id": x.id, "reference": x.reference, "statut": x.statut} for x in d.declarations]
