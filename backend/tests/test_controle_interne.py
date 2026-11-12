"""Module 8 — contrôle interne : COSO, faiblesse rend le contrôle déficient."""
from __future__ import annotations

from tests._helpers import admin_headers, mission_cycle


def test_ci_faiblesse_rend_deficient(client, db_session):
    h = admin_headers(client); _, cid = mission_cycle(db_session)
    ctrl = client.post(f"/cycles/{cid}/controle-interne", headers=h,
                       json={"intitule": "Séparation des tâches", "composante_coso": "activites_controle"}).json()
    client.post(f"/cycles/{cid}/controle-interne/{ctrl['id']}/faiblesses", headers=h,
                json={"libelle": "Cumul de fonctions", "gravite": "significative"})
    data = client.get(f"/cycles/{cid}/controle-interne", headers=h).json()
    assert data[0]["conclusion"] == "deficient" and len(data[0]["faiblesses"]) == 1


def test_composante_coso_invalide(client, db_session):
    h = admin_headers(client); _, cid = mission_cycle(db_session)
    r = client.post(f"/cycles/{cid}/controle-interne", headers=h,
                    json={"intitule": "X", "composante_coso": "inexistante"})
    assert r.status_code == 422
