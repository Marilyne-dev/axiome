"""Module 20 — Génération et téléchargement des tableaux Excel par cycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.cycles_ref import CYCLES, libelle_cycle
from app.core.database import get_db
from app.models.mission import Mission
from app.services import editions_service
from app.services.audit_service import journaliser
from app.services.excel_service import generer_cycle_xlsx, generer_dossier_xlsx

router = APIRouter(prefix="/missions/{mission_id}/excel", tags=["generation_excel"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/dossier-complet")
def telecharger_dossier(mission_id: int, db: Session = Depends(get_db),
                        user=Depends(require_permission("report:generate"))) -> StreamingResponse:
    """Classeur unique : feuille Synthèse + une Feuille Maîtresse par cycle présent."""
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    contenu = generer_dossier_xlsx(db, mission_id, edite_par=user.nom_complet or user.email)
    journaliser(db, user_id=user.id, action="excel.dossier", objet="mission", detail=str(mission_id))
    editions_service.enregistrer(db, mission_id, "dossier-complet", "xlsx",
                                 user.nom_complet or user.email)
    db.commit()
    nom = f"dossier_complet_M{mission_id}.xlsx"
    return StreamingResponse(
        iter([contenu]), media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


@router.get("/cycles")
def cycles_disponibles(mission_id: int, db: Session = Depends(get_db),
                       _=Depends(require_permission("mission:read"))) -> list[dict]:
    return [{"code": code, "libelle": libelle_cycle(code)} for code in CYCLES]


@router.get("/{code_cycle}")
def telecharger_cycle(mission_id: int, code_cycle: str, db: Session = Depends(get_db),
                      user=Depends(require_permission("report:generate"))) -> StreamingResponse:
    """Génère et renvoie le classeur (Feuille Maîtresse + travail) du cycle."""
    if code_cycle not in CYCLES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cycle inconnu : {code_cycle}")
    if not db.get(Mission, mission_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    contenu = generer_cycle_xlsx(db, mission_id, code_cycle, edite_par=user.nom_complet or user.email)
    journaliser(db, user_id=user.id, action="excel.generer", objet="mission", detail=code_cycle)
    editions_service.enregistrer(db, mission_id, f"cycle:{code_cycle}", "xlsx",
                                 user.nom_complet or user.email)
    db.commit()
    nom = f"{code_cycle}_M{mission_id}.xlsx"
    return StreamingResponse(
        iter([contenu]), media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
