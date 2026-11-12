"""Module 17 — Endpoints de génération des rapports Word/PDF."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.audit import Threshold
from app.models.mission import Mission
from app.services import editions_service
from app.services.conclusion_service import pour_note_synthese
from app.services.rapports_service import (
    docx_vers_pdf,
    feuille_garde,
    lettre_mission,
    note_synthese,
    rapport_general,
)
from app.services.synthese_service import collecter as collecter_synthese

router = APIRouter(prefix="/missions/{mission_id}/rapports", tags=["rapports"])

_MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_GENERATEURS = {
    "lettre-mission": lambda db, m: lettre_mission(m),
    "rapport-general": lambda db, m: rapport_general(m),
    "note-synthese": lambda db, m: note_synthese(
        m,
        seuil=(t.seuil_signification if (t := db.query(Threshold).filter_by(mission_id=m.id).first()) else None),
        conclusions=pour_note_synthese(db, m.id),
    ),
    "feuille-garde": lambda db, m: feuille_garde(m, collecter_synthese(db, m.id)),
}


@router.get("/{type_rapport}")
def generer_rapport(mission_id: int, type_rapport: str,
                    format: str = Query("docx", pattern="^(docx|pdf)$"),
                    db: Session = Depends(get_db),
                    user=Depends(require_permission("report:generate"))) -> StreamingResponse:
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    gen = _GENERATEURS.get(type_rapport)
    if not gen:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "Type inconnu (lettre-mission | rapport-general | note-synthese | feuille-garde)")
    contenu = gen(db, mission)
    edite_par = user.nom_complet or user.email
    if type_rapport == "feuille-garde":
        contenu = feuille_garde(mission, collecter_synthese(db, mission_id), edite_par=edite_par)
    editions_service.enregistrer(db, mission_id, type_rapport, format, edite_par)
    base = f"AXIOME_{type_rapport}_{mission_id}"
    if format == "pdf":
        contenu = docx_vers_pdf(contenu)
        return StreamingResponse(iter([contenu]), media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{base}.pdf"'})
    return StreamingResponse(iter([contenu]), media_type=_MIME_DOCX,
                             headers={"Content-Disposition": f'attachment; filename="{base}.docx"'})
