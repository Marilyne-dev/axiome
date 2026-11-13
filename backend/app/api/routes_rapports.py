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


# ---- Rapport général signé : opinion choisie par le signataire ----
from typing import Literal  # noqa: E402

from pydantic import BaseModel, Field  # noqa: E402

from app.services.rapport_general_service import (  # noqa: E402
    erreurs_version_finale,
    points_cles_suggeres,
    rapport_general_signe,
)


class OpinionIn(BaseModel):
    opinion: Literal["sans_reserve", "avec_reserves", "refus"] | None = None
    motif: str = Field("", max_length=5000)
    points_cles: list[str] = Field(default_factory=list, max_length=30)
    finale: bool = False


@router.get("/rapport-general/suggestions")
def suggestions_rapport_general(mission_id: int, db: Session = Depends(get_db),
                                user=Depends(require_permission("report:generate"))):
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    return {"points_cles": points_cles_suggeres(collecter_synthese(db, mission_id))}


@router.post("/rapport-general")
def generer_rapport_general(mission_id: int, saisie: OpinionIn,
                            format: str = Query("docx", pattern="^(docx|pdf)$"),
                            db: Session = Depends(get_db),
                            user=Depends(require_permission("report:generate"))) -> StreamingResponse:
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    if saisie.finale:
        erreurs = erreurs_version_finale(saisie.opinion, saisie.motif, saisie.points_cles)
        if erreurs:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, " ".join(erreurs))
    edite_par = user.nom_complet or user.email
    contenu = rapport_general_signe(
        mission, opinion=saisie.opinion, motif=saisie.motif, points_cles=saisie.points_cles,
        finale=saisie.finale, signataire=edite_par)
    type_ed = "rapport-general" if saisie.finale else "rapport-general-projet"
    editions_service.enregistrer(db, mission_id, type_ed, format, edite_par)
    base = f"AXIOME_{type_ed}_{mission_id}"
    if format == "pdf":
        contenu = docx_vers_pdf(contenu)
        return StreamingResponse(iter([contenu]), media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{base}.pdf"'})
    return StreamingResponse(iter([contenu]), media_type=_MIME_DOCX,
                             headers={"Content-Disposition": f'attachment; filename="{base}.docx"'})