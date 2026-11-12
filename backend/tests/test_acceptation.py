"""Tests Module 3 — Acceptation : workflow, garde-fou conflit, lettre de mission."""
from __future__ import annotations

from app.models.client import Client
from app.models.mission import Mission


def _admin(client):
    return {"Authorization": f"Bearer {client.post('/auth/login', json={'email':'admin@axiome.io','password':'Test!2026'}).json()['access_token']}"}


def _mission(db):
    c = Client(cabinet_id=None, raison_sociale="Zeta", pays="France")
    # cabinet_id NOT NULL -> créer un cabinet minimal
    from app.models.cabinet import Cabinet
    cab = Cabinet(nom="C", pays="France"); db.add(cab); db.flush()
    c.cabinet_id = cab.id
    db.add(c); db.flush()
    m = Mission(client_id=c.id, intitule="Mission Zeta", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.commit()
    return m.id


def test_acceptation_puis_decision(client, db_session):
    h = _admin(client); mid = _mission(db_session)
    client.put(f"/missions/{mid}/acceptation", headers=h, json={
        "independance_ok": True, "conflit_interet": False, "kyc_ok": True,
        "continuite_exploitation_ok": True, "niveau_risque_global": "faible", "questionnaire": {"q1": "oui"}})
    r = client.post(f"/missions/{mid}/acceptation/decision", headers=h,
                    json={"decision": "acceptee", "motivation": "Risque faible"})
    assert r.status_code == 200 and r.json()["decision"] == "acceptee"


def test_acceptation_bloquee_si_conflit(client, db_session):
    h = _admin(client); mid = _mission(db_session)
    client.put(f"/missions/{mid}/acceptation", headers=h, json={
        "independance_ok": True, "conflit_interet": True, "kyc_ok": True,
        "continuite_exploitation_ok": True, "niveau_risque_global": "eleve", "questionnaire": {}})
    r = client.post(f"/missions/{mid}/acceptation/decision", headers=h,
                    json={"decision": "acceptee", "motivation": "x"})
    assert r.status_code == 409  # conflit non levé -> acceptation interdite


def test_lettre_mission_apres_acceptation(client, db_session):
    h = _admin(client); mid = _mission(db_session)
    client.put(f"/missions/{mid}/acceptation", headers=h, json={
        "independance_ok": True, "conflit_interet": False, "kyc_ok": True,
        "continuite_exploitation_ok": True, "niveau_risque_global": "faible", "questionnaire": {}})
    client.post(f"/missions/{mid}/acceptation/decision", headers=h, json={"decision": "acceptee"})
    r = client.post(f"/missions/{mid}/acceptation/lettre-mission", headers=h)
    assert r.status_code == 200 and "Lettre de mission" in r.json()["corps"]
