"""Module 5 — Import de la balance générale (upload xlsx)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import settings
from app.core.database import get_db
from app.models.balance import LigneBalance
from app.models.mission import Mission
from app.models.user import User
from app.services import fec_import_service
from app.services.audit_service import journaliser
from app.services.fec_service import parser_fec
from app.services.import_service import importer_balance

router = APIRouter(prefix="/missions/{mission_id}/import", tags=["import"])


@router.post("/balance")
async def import_balance(
    mission_id: int, fichier: UploadFile = File(...),
    feuille: str = "Table_BG", db: Session = Depends(get_db),
    user: User = Depends(require_permission("mission:write")),
) -> dict:
    """Importe une balance (xlsx) et la rattache à la mission (réimport idempotent)."""
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    if not fichier.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Format attendu : .xlsx")
    contenu = await fichier.read()
    try:
        resultat = importer_balance(db, mission_id, contenu, feuille)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    journaliser(db, user_id=user.id, action="balance.import", objet="mission",
                detail=f"{resultat['lignes_importees']} lignes")
    db.commit()
    return resultat


@router.post("/fec")
async def import_fec(
    mission_id: int, fichier: UploadFile = File(...), confirmer: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mission:write")),
) -> dict:
    """Importe un FEC (DGFiP) : le grand livre est agrégé en balance et remplace celle de la mission.

    Garde-fou : si la mission a déjà une balance, l'import est refusé (409) tant que l'appelant
    n'a pas confirmé explicitement (`confirmer=true`). Le fichier est vérifié AVANT toute écriture,
    pour qu'un fichier illisible ne détruise jamais la balance existante.
    """
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    nom = (fichier.filename or "").lower()
    if not nom.endswith((".txt", ".csv", ".fec")):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Format attendu : fichier FEC (.txt, .csv ou .fec).")
    brut = await fichier.read()
    if len(brut) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                            f"Fichier trop volumineux (maximum {settings.max_upload_mb} Mo).")
    try:
        contenu = brut.decode("utf-8")
    except UnicodeDecodeError:
        contenu = brut.decode("latin-1", errors="replace")
    try:
        apercu = parser_fec(contenu)
    except Exception as exc:  # noqa: BLE001 — fichier illisible : message clair, aucune écriture
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Fichier FEC illisible. Vérifiez qu'il s'agit bien d'un FEC "
                            "(colonnes CompteNum, Debit, Credit).") from exc
    if not apercu.lignes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Aucune écriture exploitable dans ce fichier. Vérifiez qu'il s'agit bien d'un FEC "
                            "(colonnes CompteNum, Debit, Credit).")
    existe = db.query(LigneBalance).filter_by(mission_id=mission_id).first() is not None
    if existe and not confirmer:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Une balance existe déjà pour cette mission. Confirmez pour la remplacer par ce FEC.")
    resultat = fec_import_service.importer_fec(db, mission_id, contenu)
    journaliser(db, user_id=user.id, action="fec.import", objet="mission",
                detail=f"{resultat['nb_comptes']} comptes")
    db.commit()
    return resultat
