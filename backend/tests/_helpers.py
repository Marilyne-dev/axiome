"""Helpers de test Phase 4 : token admin, mission et cycle."""
from __future__ import annotations

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Cycle, Mission


def admin_headers(client):
    tok = client.post("/auth/login", json={"email": "admin@axiome.io", "password": "Test!2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def mission_cycle(db, code="TRESORERIE"):
    cab = Cabinet(nom="C", pays="France"); db.add(cab); db.flush()
    c = Client(cabinet_id=cab.id, raison_sociale="Theta", pays="France"); db.add(c); db.flush()
    m = Mission(client_id=c.id, intitule="M Theta", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.flush()
    cy = Cycle(mission_id=m.id, code=code, libelle=code.title())
    db.add(cy); db.commit()
    return m.id, cy.id
