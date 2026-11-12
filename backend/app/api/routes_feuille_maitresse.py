"""Module 20 — Feuille Maîtresse d'un cycle (JSON + export Excel)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.balance import LigneBalance
from app.models.client import Client
from app.models.mission import Cycle, Mission
from app.models.user import User
from app.services.audit_service import journaliser
from app.services.excel_fm_service import exporter_feuille_maitresse
from app.services.feuille_maitresse_service import CYCLES_PCG, construire_fm

router = APIRouter(prefix="/cycles/{cycle_id}/feuille-maitresse", tags=["feuille_maitresse"])


def _contexte(db: Session, cycle_id: int):
    cycle = db.get(Cycle, cycle_id)
    if not cycle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    if cycle.code.upper() not in CYCLES_PCG:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Cycle non cartographié PCG : {cycle.code}")
    mission = db.get(Mission, cycle.mission_id)

    def _bal(ex: str) -> dict[str, tuple[str, float]]:
        return {l.compte: (l.libelle, l.solde)
                for l in db.query(LigneBalance).filter_by(mission_id=mission.id, exercice=ex).all()}

    return cycle, mission, _bal("N"), _bal("N-1")


@router.get("")
def obtenir(cycle_id: int, db: Session = Depends(get_db),
            _=Depends(require_permission("cycle:read"))) -> dict:
    cycle, mission, bal_n, bal_n1 = _contexte(db, cycle_id)
    if not bal_n:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucune balance N importée pour cette mission.")
    fm = construire_fm(cycle.code, bal_n, bal_n1)
    return {
        "cycle": fm.cycle, "total_n": fm.total_n, "total_n1": fm.total_n1,
        "total_variation": fm.total_variation,
        "lignes": [{"compte": l.compte, "libelle": l.libelle, "solde_n": l.solde_n,
                    "solde_n1": l.solde_n1, "variation": l.variation, "pourcentage": l.pourcentage}
                   for l in fm.lignes],
    }


@router.post("/export")
def exporter(cycle_id: int, db: Session = Depends(get_db),
             user: User = Depends(require_permission("cycle:write"))) -> FileResponse:
    cycle, mission, bal_n, bal_n1 = _contexte(db, cycle_id)
    if not bal_n:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucune balance N importée pour cette mission.")
    fm = construire_fm(cycle.code, bal_n, bal_n1)
    client = db.get(Client, mission.client_id)
    sortie = Path(tempfile.gettempdir()) / f"FM_{cycle.code}_{mission.id}.xlsx"
    exporter_feuille_maitresse(
        fm, client=client.raison_sociale if client else "Client",
        exercice_cloture=mission.exercice or "N", chemin_sortie=sortie,
    )
    journaliser(db, user_id=user.id, action="fm.export", objet="cycle", detail=cycle.code)
    db.commit()
    return FileResponse(
        path=str(sortie),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"FM_{cycle.code}.xlsx",
    )
