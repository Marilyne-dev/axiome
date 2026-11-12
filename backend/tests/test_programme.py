"""Module 9 — programme : génération par code de cycle."""
from __future__ import annotations

from tests._helpers import admin_headers, mission_cycle


def test_generation_programme_tresorerie(client, db_session):
    h = admin_headers(client); _, cid = mission_cycle(db_session, code="TRESORERIE")
    r = client.post(f"/cycles/{cid}/programme/generer", headers=h).json()
    assert r["procedures_ajoutees"] == 3
    prog = client.get(f"/cycles/{cid}/programme", headers=h).json()
    refs = {p["reference"] for p in prog["procedures"]}
    assert {"TR-1", "TR-2", "TR-3"} <= refs


def test_generation_idempotente(client, db_session):
    h = admin_headers(client); _, cid = mission_cycle(db_session, code="EMPRUNTS")
    client.post(f"/cycles/{cid}/programme/generer", headers=h)
    r2 = client.post(f"/cycles/{cid}/programme/generer", headers=h).json()
    assert r2["procedures_ajoutees"] == 0  # pas de doublon
