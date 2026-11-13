"""Tâches de fond : lancement d'un traitement lourd, suivi et récupération du résultat."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.api.deps import get_current_user, require_permission
from app.core.database import SessionLocal
from app.models.user import User
from app.services import editions_service, taches_service
from app.services.audit_service import journaliser
from app.services.excel_service import generer_dossier_xlsx

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Monté avec la garde de cloisonnement par mission (cf. main.py).
router_missions = APIRouter(prefix="/missions/{mission_id}/excel", tags=["taches"])
# Suivi des tâches : réservé à leur propriétaire.
router = APIRouter(prefix="/taches", tags=["taches"])


@router_missions.post("/dossier-complet/async", status_code=status.HTTP_202_ACCEPTED)
def lancer_dossier_complet(mission_id: int, user: User = Depends(require_permission("report:generate"))) -> dict:
    """Génère le classeur complet en arrière-plan (utile pour les grosses missions)."""
    nom_user = user.nom_complet or user.email
    uid = user.id

    def travail() -> tuple[bytes, str, str]:
        db = SessionLocal()  # session propre au thread
        try:
            contenu = generer_dossier_xlsx(db, mission_id, edite_par=nom_user)
            journaliser(db, user_id=uid, action="excel.dossier.async", objet="mission", detail=str(mission_id))
            editions_service.enregistrer(db, mission_id, "dossier-complet", "xlsx", nom_user)
            db.commit()
            return contenu, f"dossier_complet_M{mission_id}.xlsx", _XLSX
        finally:
            db.close()

    tid = taches_service.lancer(travail, uid, f"Dossier complet — mission {mission_id}")
    return {"id": tid, "statut": "en_cours", "suivi": f"/taches/{tid}"}


@router.get("/{tache_id}")
def suivre(tache_id: str, user: User = Depends(get_current_user)) -> dict:
    e = taches_service.etat(tache_id, user.id, user.has_role("SUPERADMIN"))
    if not e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable")
    return e


@router.get("/{tache_id}/resultat")
def recuperer(tache_id: str, user: User = Depends(get_current_user)) -> Response:
    r = taches_service.resultat(tache_id, user.id, user.has_role("SUPERADMIN"))
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Résultat indisponible (tâche inconnue ou non terminée)")
    contenu, nom, mime = r
    return Response(contenu, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{nom}"'})
