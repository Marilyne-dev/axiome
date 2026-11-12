"""Tests Module 4 — Planification : plan, jalons, équipe, budget, totaux."""
from __future__ import annotations

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.user import User


def _admin(client):
    tok = client.post('/auth/login', json={'email':'admin@axiome.io','password':'Test!2026'}).json()['access_token']
    return {"Authorization": f"Bearer {tok}"}


def _mission(db):
    cab = Cabinet(nom="C", pays="France"); db.add(cab); db.flush()
    c = Client(cabinet_id=cab.id, raison_sociale="Eta", pays="France"); db.add(c); db.flush()
    m = Mission(client_id=c.id, intitule="Mission Eta", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.commit()
    return m.id


def test_plan_jalon_budget_totaux(client, db_session):
    h = _admin(client); mid = _mission(db_session)
    client.put(f"/missions/{mid}/planification", headers=h,
               json={"approche": "substantive", "honoraires": 15000, "devise": "EUR"})
    client.post(f"/missions/{mid}/planification/jalons", headers=h, json={"libelle": "Intérim"})
    client.post(f"/missions/{mid}/planification/budget", headers=h, json={"poste": "Terrain", "montant": 8000})
    client.post(f"/missions/{mid}/planification/budget", headers=h, json={"poste": "Revue", "montant": 4000})
    admin_id = db_session.query(User).filter_by(email="admin@axiome.io").first().id
    client.post(f"/missions/{mid}/planification/equipe", headers=h,
                json={"user_id": admin_id, "role_mission": "chef", "heures_estimees": 40})
    data = client.get(f"/missions/{mid}/planification", headers=h).json()
    assert data["total_budget"] == 12000
    assert data["total_heures"] == 40
    assert len(data["jalons"]) == 1


def test_affectation_user_inconnu(client, db_session):
    h = _admin(client); mid = _mission(db_session)
    r = client.post(f"/missions/{mid}/planification/equipe", headers=h,
                    json={"user_id": 99999, "heures_estimees": 5})
    assert r.status_code == 422
