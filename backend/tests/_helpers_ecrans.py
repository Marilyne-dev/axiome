"""Fabriques communes aux tests des écrans de la phase 8."""
from __future__ import annotations

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Cycle, Mission


def ck(client):
    return client.post("/login", data={"email": "admin@axiome.io", "password": "Test!2026"},
                       follow_redirects=False).cookies


def mission(db, avec_cycle=False):
    cab = db.query(Cabinet).first()
    if cab is None:
        cab = Cabinet(nom="Cab"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Alpha"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit", referentiel="PCG_FR",
                pays="France", devise="EUR", exercice="2025"); db.add(m); db.flush()
    cid = None
    if avec_cycle:
        cy = Cycle(mission_id=m.id, code="TRESORERIE", libelle="Trésorerie"); db.add(cy); db.flush()
        cid = cy.id
    db.commit()
    return (m.id, cid) if avec_cycle else m.id
