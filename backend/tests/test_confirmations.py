"""Module 12 — confirmations : création, type invalide, relance."""
from __future__ import annotations

from tests._helpers import admin_headers, mission_cycle


def test_creation_et_relance(client, db_session):
    h = admin_headers(client); mid, _ = mission_cycle(db_session)
    cid = client.post(f"/missions/{mid}/confirmations", headers=h,
                      json={"tiers": "BNP Paribas", "type_tiers": "banque"}).json()["id"]
    r = client.post(f"/missions/{mid}/confirmations/{cid}/relancer", headers=h)
    assert r.status_code == 200 and r.json()["statut"] == "relancee"


def test_type_tiers_invalide(client, db_session):
    h = admin_headers(client); mid, _ = mission_cycle(db_session)
    r = client.post(f"/missions/{mid}/confirmations", headers=h, json={"tiers": "X", "type_tiers": "extraterrestre"})
    assert r.status_code == 422
