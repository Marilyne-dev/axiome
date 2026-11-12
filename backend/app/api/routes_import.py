"""Module 5 — Import de la balance générale (upload xlsx)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.mission import Mission
from app.models.user import User
from app.services.audit_service import journaliser
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
