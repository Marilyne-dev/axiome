"""Cloisonnement par cabinet des routes JSON `/missions/{id}/...` et `/cycles/{id}/...`.

Sans ces gardes, tout utilisateur connecté pouvait lire ou modifier la mission d'un AUTRE cabinet en
devinant son identifiant (les routes ne contrôlaient que la permission, pas le cabinet). Une mission
hors périmètre répond 404 (et non 403) pour ne pas révéler son existence.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.client import Client
from app.models.mission import Cycle, Mission
from app.models.user import User
from app.services import billing_service


def mission_du_cabinet(db: Session, user: User, mission_id: int) -> Mission:
    """Retourne la mission si elle appartient au cabinet de l'utilisateur (l'éditeur voit tout), sinon 404."""
    m = db.get(Mission, mission_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    if user.has_role("SUPERADMIN"):
        return m
    cli = db.get(Client, m.client_id)
    if not user.cabinet_id or not cli or cli.cabinet_id != user.cabinet_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission introuvable")
    abo = billing_service.abonnement_du_cabinet(db, user.cabinet_id)
    if billing_service.statut_effectif(abo) != "actif":
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "abonnement_inactif")
    return m


def garde_mission(mission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    mission_du_cabinet(db, user, mission_id)


def garde_cycle(cycle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    cy = db.get(Cycle, cycle_id)
    if not cy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle introuvable")
    mission_du_cabinet(db, user, cy.mission_id)
